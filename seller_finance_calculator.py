import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from functools import lru_cache
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION
CONFIG = {
    "annual_interest_rate": 0.00,
    "assignment_fee": 5000.0,
    "closing_cost_percent_of_offer": 0.02,
    "monthly_capex_rate": 0.10,
    "monthly_prop_mgmt_rate": 0.10,
    "monthly_vacancy_rate": 0.0,
    "appreciation_per_year": 0.045,
    "max_amortization_years": 45.0,
    "rehab_rates": {"light": 20.0, "medium": 35.0, "heavy": 60.0},
    "rehab_caps": {"arv_cap_percent": 0.15, "budget_cap_percent": 0.35},
    "offers": {
        "owner_favored": {
            "monthly_cash_flow_start": 200.0,
            "coc_threshold": 11.0,
            "entry_fee_range": (21.0, 23.0),
            "appreciation_profit_percent_of_listed": 0.15,
            "balloon_period": 5
        },
        "balanced": {
            "target_coc_percent": 14.0,
            "monthly_cash_flow_min": 200.0,
            "balloon_period": 6
        },
        "buyer_favored": {
            "target_coc_percent": 17.0,
            "entry_fee_percent_target": 15.0,
            "balloon_period": 7,
        }
    },
    "adjustment_rules": {
        "cash_flow_increase_percent": 0.02,
        "entry_fee_reduction_percent": 0.5,
        "max_iterations": 100
    }
}


# --- DATA CLASSES ---
@dataclass
class PropertyData:
    listed_price: float
    monthly_rent: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa_fee: float
    monthly_other_fees: float
    arv: float

    def __post_init__(self):
        """Validate property data after initialization."""
        if self.listed_price <= 0:
            raise ValueError("Listed price must be positive")
        if self.monthly_rent <= 0:
            raise ValueError("Monthly rent must be positive")
        if self.arv <= 0:
            raise ValueError("ARV must be positive")

    @property
    def total_monthly_fixed_expenses(self) -> float:
        """Calculate total monthly fixed expenses."""
        return (self.monthly_property_tax + self.monthly_insurance +
                self.monthly_hoa_fee + self.monthly_other_fees)


@dataclass
class OfferResult:
    offer_type: str
    is_buyable: bool
    unbuyable_reason: str
    final_offer_price: float
    final_coc_percent: float
    final_monthly_cash_flow: float
    final_entry_fee_percent: float
    final_entry_fee_amount: float
    down_payment: float
    down_payment_percent: float
    loan_amount: float
    monthly_payment: float
    balloon_period: int
    appreciation_profit: float
    rehab_cost: float
    amortization_years: float
    principal_paid: float
    balloon_payment: float

    def __post_init__(self):
        """Validate offer result after initialization."""
        if self.final_offer_price < 0:
            raise ValueError("Offer price cannot be negative")


@dataclass
class CalculatedExpenses:
    """Cache for calculated expenses to avoid repeated calculations."""
    non_debt_expenses: float
    total_variable_expenses: float

    @classmethod
    def from_property_data(cls, property_data: PropertyData, config: Dict) -> 'CalculatedExpenses':
        rent = property_data.monthly_rent
        variable_expenses = (rent * config["monthly_vacancy_rate"] +
                             rent * config["monthly_capex_rate"] +
                             rent * config["monthly_prop_mgmt_rate"])

        non_debt_expenses = property_data.total_monthly_fixed_expenses + variable_expenses

        return cls(non_debt_expenses=non_debt_expenses, total_variable_expenses=variable_expenses)


class SellerFinanceCalculator:
    """Optimized calculator for seller financing scenarios."""

    def __init__(self, config: Dict = CONFIG):
        self.config = config
        self._validate_config()
        logger.info("Calculator initialized with configuration")

    def _validate_config(self):
        """Validate configuration parameters."""
        required_keys = ["rehab_rates", "rehab_caps", "offers", "adjustment_rules"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    @staticmethod
    def calculate_coc(monthly_cash_flow: float, entry_fee: float) -> float:
        """Calculate Cash on Cash return percentage."""
        return (monthly_cash_flow * 12 / entry_fee) * 100 if entry_fee > 0 else 0.0

    @lru_cache(maxsize=128)
    def calculate_rehab_cost(self, light: float, medium: float, heavy: float) -> float:
        """Calculate total rehab cost with caching for repeated calculations."""
        rates = self.config["rehab_rates"]
        return (light * rates["light"] + medium * rates["medium"] + heavy * rates["heavy"])

    def calculate_rehab_cost_from_dict(self, repairs: Dict[str, float]) -> float:
        """Wrapper for dictionary input that leverages caching."""
        return self.calculate_rehab_cost(
            repairs.get("light", 0),
            repairs.get("medium", 0),
            repairs.get("heavy", 0)
        )

    def check_rehab_buyability(self, rehab_cost: float, arv: float, offer_price: float) -> Tuple[bool, str]:
        """Check if rehab costs are within acceptable limits."""
        caps = self.config["rehab_caps"]

        # ARV cap check
        max_rehab_arv = caps["arv_cap_percent"] * arv
        if rehab_cost > max_rehab_arv:
            return False, f"Rehab cost (${rehab_cost:,.2f}) exceeds {caps['arv_cap_percent']:.0%} of ARV (${max_rehab_arv:,.2f})."

        # Budget cap check
        max_rehab_budget = caps["budget_cap_percent"] * offer_price
        if rehab_cost > max_rehab_budget:
            return False, f"Rehab cost (${rehab_cost:,.2f}) exceeds {caps['budget_cap_percent']:.0%} of Offer Price (${max_rehab_budget:,.2f})."

        return True, ""

    @lru_cache(maxsize=64)
    def calculate_appreciated_value(self, base_price: float, balloon_years: int) -> float:
        """Calculate appreciated value with caching."""
        return base_price * ((1 + self.config["appreciation_per_year"]) ** balloon_years)

    @staticmethod
    def calculate_amortization_period(loan_amount: float, monthly_payment: float) -> float:
        """Calculate amortization period in years."""
        return loan_amount / (monthly_payment * 12) if monthly_payment > 0 else float('inf')

    def _run_owner_adjustment_loop(self, offer_price: float) -> Tuple[float, float]:
        """Optimized owner adjustment loop with early termination."""
        offer_cfg = self.config["offers"]["owner_favored"]
        adj_rules = self.config["adjustment_rules"]

        coc_threshold = offer_cfg["coc_threshold"]
        entry_fee_percent = offer_cfg["entry_fee_range"][1]
        entry_fee_lower_bound = offer_cfg["entry_fee_range"][0]
        monthly_cash_flow = offer_cfg["monthly_cash_flow_start"]

        max_iterations = adj_rules.get("max_iterations", 100)

        for iteration in range(max_iterations):
            current_entry_fee_amount = offer_price * (entry_fee_percent / 100)
            current_coc = self.calculate_coc(monthly_cash_flow, current_entry_fee_amount)

            if current_coc >= coc_threshold:
                logger.debug(f"Owner adjustment converged after {iteration} iterations")
                break

            # Try cash flow adjustment first
            monthly_cash_flow *= (1 + adj_rules["cash_flow_increase_percent"])
            coc_after_cf_adj = self.calculate_coc(monthly_cash_flow, current_entry_fee_amount)

            if coc_after_cf_adj >= coc_threshold:
                break

            # Try entry fee adjustment
            entry_fee_percent = max(
                entry_fee_lower_bound,
                entry_fee_percent - adj_rules["entry_fee_reduction_percent"]
            )

            # Check if we've hit the lower bound
            if entry_fee_percent == entry_fee_lower_bound:
                new_entry_fee_amount = offer_price * (entry_fee_percent / 100)
                if self.calculate_coc(monthly_cash_flow, new_entry_fee_amount) >= coc_threshold:
                    break

        return monthly_cash_flow, entry_fee_percent

    def _calculate_financial_metrics(self, offer_price: float, monthly_cash_flow: float,
                                     entry_fee_percent: float, monthly_payment: float,
                                     balloon_period: int, appreciation_profit: float,
                                     rehab_cost: float) -> Dict[str, float]:
        """Calculate all financial metrics in one place to avoid duplication."""
        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        dp_percent = (down_payment / offer_price) * 100 if offer_price > 0 else 0
        loan_amount = offer_price - down_payment

        coc = self.calculate_coc(monthly_cash_flow, entry_fee_amount)
        amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
        principal_paid = monthly_payment * 12 * balloon_period
        balloon_payment = max(0.0, loan_amount - principal_paid)

        return {
            'entry_fee_amount': entry_fee_amount,
            'closing_cost': closing_cost,
            'down_payment': down_payment,
            'dp_percent': dp_percent,
            'loan_amount': loan_amount,
            'coc': coc,
            'amortization': amortization,
            'principal_paid': principal_paid,
            'balloon_payment': balloon_payment
        }

    def _validate_offer_viability(self, monthly_payment: float, down_payment: float) -> Tuple[bool, str]:
        """Validate if an offer is viable based on payment and down payment."""
        if monthly_payment <= 0:
            return False, "Monthly payment is not positive."
        if down_payment < 0:
            return False, "Down payment is negative."
        return True, ""

    def calculate_max_owner_favored_offer(self, property_data: PropertyData, repairs: Dict[str, float]) -> OfferResult:
        """Calculate maximum owner-favored offer."""
        offer_cfg = self.config["offers"]["owner_favored"]
        appreciation_profit = property_data.listed_price * offer_cfg["appreciation_profit_percent_of_listed"]
        balloon_period = offer_cfg["balloon_period"]

        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        offer_price = appreciated_value - appreciation_profit

        rehab_cost = self.calculate_rehab_cost_from_dict(repairs)

        # Check rehab buyability
        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        if not is_buyable:
            return self._create_unbuyable_result("Max Owner Favored", unbuyable_reason, offer_price, rehab_cost,
                                                 balloon_period, appreciation_profit)

        target_cash_flow, final_entry_fee_percent = self._run_owner_adjustment_loop(offer_price)

        # Calculate expenses once
        expenses = CalculatedExpenses.from_property_data(property_data, self.config)
        monthly_payment = property_data.monthly_rent - expenses.non_debt_expenses - target_cash_flow

        return self._create_offer_result("Max Owner Favored", is_buyable, unbuyable_reason, offer_price,
                                         target_cash_flow, final_entry_fee_percent, monthly_payment, balloon_period,
                                         appreciation_profit, rehab_cost)

    def calculate_max_buyer_favored_offer(self, property_data: PropertyData, repairs: Dict[str, float]) -> OfferResult:
        """Calculate maximum buyer-favored offer."""
        offer_cfg = self.config["offers"]["buyer_favored"]
        offer_price = property_data.listed_price
        balloon_period = offer_cfg["balloon_period"]

        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        appreciation_profit = appreciated_value - offer_price

        rehab_cost = self.calculate_rehab_cost_from_dict(repairs)

        # Check rehab buyability
        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        if not is_buyable:
            return self._create_unbuyable_result("Max Buyer Favored", unbuyable_reason, offer_price, rehab_cost,
                                                 balloon_period, appreciation_profit)

        entry_fee_percent = offer_cfg["entry_fee_percent_target"]
        target_coc = offer_cfg["target_coc_percent"]

        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        initial_cash_flow = (target_coc / 100) * entry_fee_amount / 12

        # Calculate expenses once
        expenses = CalculatedExpenses.from_property_data(property_data, self.config)
        initial_monthly_payment = property_data.monthly_rent - expenses.non_debt_expenses - initial_cash_flow

        # Calculate financial metrics
        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        loan_amount = offer_price - down_payment

        initial_amortization = self.calculate_amortization_period(loan_amount, initial_monthly_payment)

        # Adjust if amortization exceeds maximum
        if initial_amortization <= self.config["max_amortization_years"]:
            final_monthly_cash_flow = initial_cash_flow
            final_monthly_payment = initial_monthly_payment
        else:
            max_amortization = self.config["max_amortization_years"]
            final_monthly_payment = loan_amount / (max_amortization * 12)
            final_monthly_cash_flow = property_data.monthly_rent - expenses.non_debt_expenses - final_monthly_payment

        return self._create_offer_result("Max Buyer Favored", is_buyable, unbuyable_reason, offer_price,
                                         final_monthly_cash_flow, entry_fee_percent, final_monthly_payment,
                                         balloon_period, appreciation_profit, rehab_cost)

    def calculate_balanced_offer(self, owner_offer: OfferResult, buyer_offer: OfferResult,
                                 property_data: PropertyData, repairs: Dict[str, float]) -> OfferResult:
        """Calculate balanced offer based on owner and buyer offers."""
        offer_cfg = self.config["offers"]["balanced"]

        # Average the key metrics
        offer_price = (owner_offer.final_offer_price + buyer_offer.final_offer_price) / 2
        entry_fee_percent = (owner_offer.final_entry_fee_percent + buyer_offer.final_entry_fee_percent) / 2
        balloon_period = offer_cfg["balloon_period"]

        rehab_cost = self.calculate_rehab_cost_from_dict(repairs)

        # Check rehab buyability
        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        appreciation_profit = appreciated_value - offer_price

        if not is_buyable:
            return self._create_unbuyable_result("Balanced", unbuyable_reason, offer_price, rehab_cost,
                                                 balloon_period, appreciation_profit)

        # Calculate cash flow based on target COC
        target_coc = offer_cfg["target_coc_percent"]
        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        monthly_cash_flow = (target_coc / 100) * entry_fee_amount / 12

        # Check minimum cash flow requirement
        if monthly_cash_flow < offer_cfg["monthly_cash_flow_min"]:
            is_buyable = False
            unbuyable_reason = f"Calculated cash flow (${monthly_cash_flow:,.2f}) is below minimum of ${offer_cfg['monthly_cash_flow_min']:.2f}."

        # Calculate expenses once
        expenses = CalculatedExpenses.from_property_data(property_data, self.config)
        monthly_payment = property_data.monthly_rent - expenses.non_debt_expenses - monthly_cash_flow

        return self._create_offer_result("Balanced", is_buyable, unbuyable_reason, offer_price,
                                         monthly_cash_flow, entry_fee_percent, monthly_payment,
                                         balloon_period, appreciation_profit, rehab_cost)

    def _create_offer_result(self, offer_type: str, is_buyable: bool, unbuyable_reason: str,
                             offer_price: float, monthly_cash_flow: float, entry_fee_percent: float,
                             monthly_payment: float, balloon_period: int, appreciation_profit: float,
                             rehab_cost: float) -> OfferResult:
        """Create offer result with comprehensive financial calculations."""

        # Calculate all financial metrics
        metrics = self._calculate_financial_metrics(
            offer_price, monthly_cash_flow, entry_fee_percent, monthly_payment,
            balloon_period, appreciation_profit, rehab_cost
        )

        # Final viability check
        if is_buyable:
            viability_check, viability_reason = self._validate_offer_viability(
                monthly_payment, metrics['down_payment']
            )
            if not viability_check:
                is_buyable = False
                unbuyable_reason = viability_reason

        return OfferResult(
            offer_type=offer_type,
            is_buyable=is_buyable,
            unbuyable_reason=unbuyable_reason,
            final_offer_price=offer_price,
            final_coc_percent=metrics['coc'],
            final_monthly_cash_flow=monthly_cash_flow,
            final_entry_fee_percent=entry_fee_percent,
            final_entry_fee_amount=metrics['entry_fee_amount'],
            down_payment=metrics['down_payment'],
            down_payment_percent=metrics['dp_percent'],
            loan_amount=metrics['loan_amount'],
            monthly_payment=monthly_payment,
            balloon_period=balloon_period,
            appreciation_profit=appreciation_profit,
            rehab_cost=rehab_cost,
            amortization_years=metrics['amortization'],
            principal_paid=metrics['principal_paid'],
            balloon_payment=metrics['balloon_payment']
        )

    def _create_unbuyable_result(self, offer_type: str, reason: str, offer_price: float,
                                 rehab_cost: float, balloon_period: int, appreciation_profit: float) -> OfferResult:
        """Create standardized unbuyable result."""
        return OfferResult(
            offer_type=offer_type,
            is_buyable=False,
            unbuyable_reason=reason,
            final_offer_price=offer_price,
            rehab_cost=rehab_cost,
            balloon_period=balloon_period,
            appreciation_profit=appreciation_profit,
            # Zero out all financial metrics for failed offers
            final_coc_percent=0, final_monthly_cash_flow=0, final_entry_fee_percent=0,
            final_entry_fee_amount=0, down_payment=0, down_payment_percent=0,
            loan_amount=0, monthly_payment=0, amortization_years=0,
            principal_paid=0, balloon_payment=0
        )

    def calculate_all_offers(self, property_data: PropertyData, repairs: Dict[str, float]) -> List[OfferResult]:
        """Calculate all offer types with improved error handling."""
        try:
            owner_offer = self.calculate_max_owner_favored_offer(property_data, repairs)
            buyer_offer = self.calculate_max_buyer_favored_offer(property_data, repairs)

            # Balanced offer requires both prerequisite offers to be buyable
            if not owner_offer.is_buyable or not buyer_offer.is_buyable:
                balanced_offer = self._create_unbuyable_result(
                    "Balanced", "Prerequisite offer(s) are unbuyable.", 0, 0, 0, 0
                )
            else:
                balanced_offer = self.calculate_balanced_offer(owner_offer, buyer_offer, property_data, repairs)

            return [owner_offer, buyer_offer, balanced_offer]

        except Exception as e:
            logger.error(f"Error calculating offers: {e}")
            raise


def run_and_print_test_case(case_number: int, property_data: PropertyData, repairs: Dict[str, float]):
    """Enhanced test case runner with better formatting."""
    print(f"\n{'=' * 50}")
    print(f"Test Case #{case_number}")
    print(f"{'=' * 50}")

    try:
        calculator = SellerFinanceCalculator(CONFIG)
        all_offers = calculator.calculate_all_offers(property_data, repairs)

        print("\n--- RESULTS SUMMARY ---")
        for offer in all_offers:
            print(f"\n{'-' * 30}")
            print(f"Offer Type: {offer.offer_type}")
            print(f"{'-' * 30}")

            status = "✓ BUYABLE" if offer.is_buyable else "✗ UNBUYABLE"
            print(f"Status: {status}")

            if not offer.is_buyable:
                print(f"Reason: {offer.unbuyable_reason}")

            print(f"Offer Price: ${offer.final_offer_price:,.2f}")
            print(f"Rehab Cost: ${offer.rehab_cost:,.2f}")

            if offer.is_buyable:
                print(f"Entry Fee: {offer.final_entry_fee_percent:.2f}% (${offer.final_entry_fee_amount:,.2f})")
                print(f"Monthly Cash Flow: ${offer.final_monthly_cash_flow:,.2f}")
                print(f"Monthly Payment: ${offer.monthly_payment:,.2f}")
                print(f"Cash-on-Cash Return: {offer.final_coc_percent:.2f}%")
                print(f"Down Payment: {offer.down_payment_percent:.2f}% (${offer.down_payment:,.2f})")
                print(f"Loan Amount: ${offer.loan_amount:,.2f}")
                print(f"Amortization: {offer.amortization_years:.2f} years")
                print(f"Principal Paid: ${offer.principal_paid:,.2f}")
                print(f"Balloon Payment: ${offer.balloon_payment:,.2f}")

    except Exception as e:
        print(f"Error running test case: {e}")


if __name__ == '__main__':
    # Test case
    property_2 = PropertyData(
        listed_price=87000,
        monthly_rent=1150,
        monthly_property_tax=95,
        monthly_insurance=80,
        monthly_hoa_fee=0,
        monthly_other_fees=0,
        arv=95000
    )
    repairs_2 = {"light": 35, "medium": 15, "heavy": 5}
    run_and_print_test_case(2, property_2, repairs_2)