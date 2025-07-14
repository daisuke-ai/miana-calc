import math
from typing import Dict, Tuple, List
from dataclasses import dataclass

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
            "target_coc_percent": 14.0,  # Upper bound of 11-14% range
            "monthly_cash_flow_min": 200.0,  # Minimum requirement check
            "balloon_period": 6
        },
        "buyer_favored": {
            "target_coc_percent": 17.0,  # Upper bound of 12-17% range
            "entry_fee_percent_target": 15.0,  # Lower bound of 15-17% range
            "balloon_period": 7,
        }
    },
    "adjustment_rules": {
        "cash_flow_increase_percent": 0.02,
        "entry_fee_reduction_percent": 0.5
    }
}


# --- DATA CLASSES ---
@dataclass
class PropertyData:
    listed_price: float;
    monthly_rent: float;
    monthly_property_tax: float
    monthly_insurance: float;
    monthly_hoa_fee: float;
    monthly_other_fees: float;
    arv: float


@dataclass
class OfferResult:
    offer_type: str;
    is_buyable: bool;
    unbuyable_reason: str;
    final_offer_price: float
    final_coc_percent: float;
    final_monthly_cash_flow: float;
    final_entry_fee_percent: float
    final_entry_fee_amount: float;
    down_payment: float;
    down_payment_percent: float
    loan_amount: float;
    monthly_payment: float;
    balloon_period: int;
    appreciation_profit: float
    rehab_cost: float;
    amortization_years: float;
    principal_paid: float;
    balloon_payment: float


class SellerFinanceCalculator:
    def __init__(self, config: Dict = CONFIG):
        self.config = config

    def calculate_coc(self, monthly_cash_flow: float, entry_fee: float) -> float:
        if entry_fee <= 0: return 0.0
        return (monthly_cash_flow * 12 / entry_fee) * 100

    def calculate_rehab_cost(self, repairs: Dict[str, float]) -> float:
        rates = self.config["rehab_rates"]
        return ((repairs.get("light", 0) * rates["light"]) +
                (repairs.get("medium", 0) * rates["medium"]) +
                (repairs.get("heavy", 0) * rates["heavy"]))

    def check_rehab_buyability(self, rehab_cost: float, arv: float, offer_price: float) -> Tuple[bool, str]:
        caps = self.config["rehab_caps"]
        max_rehab_arv = caps["arv_cap_percent"] * arv
        if rehab_cost > max_rehab_arv:
            return False, f"Rehab cost (${rehab_cost:,.2f}) exceeds 15% of ARV (${max_rehab_arv:,.2f})."
        max_rehab_budget = caps["budget_cap_percent"] * offer_price
        if rehab_cost > max_rehab_budget:
            return False, f"Rehab cost (${rehab_cost:,.2f}) exceeds 35% of Offer Price (${max_rehab_budget:,.2f})."
        return True, ""

    def calculate_appreciated_value(self, base_price: float, balloon_years: int) -> float:
        return base_price * ((1 + self.config["appreciation_per_year"]) ** balloon_years)

    def calculate_amortization_period(self, loan_amount: float, monthly_payment: float) -> float:
        if monthly_payment <= 0: return float('inf')
        return loan_amount / (monthly_payment * 12)

    def _run_owner_adjustment_loop(self, offer_price: float, property_data: PropertyData) -> Tuple[float, float]:
        offer_cfg = self.config["offers"]["owner_favored"]
        adj_rules = self.config["adjustment_rules"]
        coc_threshold = offer_cfg["coc_threshold"]
        entry_fee_percent = offer_cfg["entry_fee_range"][1]
        entry_fee_lower_bound = offer_cfg["entry_fee_range"][0]
        monthly_cash_flow = offer_cfg["monthly_cash_flow_start"]

        # Calculate non-debt expenses
        rent = property_data.monthly_rent
        non_debt_expenses = (property_data.monthly_property_tax + property_data.monthly_insurance +
                             property_data.monthly_hoa_fee + property_data.monthly_other_fees +
                             (rent * self.config["monthly_vacancy_rate"]) + (rent * self.config["monthly_capex_rate"]) +
                             (rent * self.config["monthly_prop_mgmt_rate"]))

        for _ in range(100):
            current_entry_fee_amount = offer_price * (entry_fee_percent / 100)

            # Check if we meet COC threshold
            current_coc = self.calculate_coc(monthly_cash_flow, current_entry_fee_amount)
            if current_coc >= coc_threshold:
                # NEW: Check amortization constraint
                closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
                rehab_cost = self.calculate_rehab_cost({})  # Assuming no repairs for adjustment loop
                down_payment = current_entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
                loan_amount = offer_price - down_payment
                monthly_payment = rent - non_debt_expenses - monthly_cash_flow

                if monthly_payment > 0:
                    amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
                    if amortization <= self.config["max_amortization_years"]:
                        break  # We found a valid solution
                    else:
                        # Cap the payment at 45 years and adjust cash flow
                        max_monthly_payment = loan_amount / (self.config["max_amortization_years"] * 12)
                        monthly_cash_flow = rent - non_debt_expenses - max_monthly_payment
                        break

            monthly_cash_flow *= (1 + adj_rules["cash_flow_increase_percent"])
            coc_after_cf_adj = self.calculate_coc(monthly_cash_flow, current_entry_fee_amount)
            if coc_after_cf_adj >= coc_threshold:
                # NEW: Check amortization constraint after cash flow adjustment
                monthly_payment = rent - non_debt_expenses - monthly_cash_flow
                if monthly_payment > 0:
                    closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
                    rehab_cost = self.calculate_rehab_cost({})
                    down_payment = current_entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
                    loan_amount = offer_price - down_payment
                    amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
                    if amortization <= self.config["max_amortization_years"]:
                        break
                    else:
                        max_monthly_payment = loan_amount / (self.config["max_amortization_years"] * 12)
                        monthly_cash_flow = rent - non_debt_expenses - max_monthly_payment
                        break

            entry_fee_percent -= adj_rules["entry_fee_reduction_percent"]
            if entry_fee_percent < entry_fee_lower_bound: entry_fee_percent = entry_fee_lower_bound
            new_entry_fee_amount = offer_price * (entry_fee_percent / 100)
            coc_after_ef_adj = self.calculate_coc(monthly_cash_flow, new_entry_fee_amount)
            if coc_after_ef_adj >= coc_threshold or entry_fee_percent == entry_fee_lower_bound:
                # NEW: Check amortization constraint after entry fee adjustment
                monthly_payment = rent - non_debt_expenses - monthly_cash_flow
                if monthly_payment > 0:
                    closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
                    rehab_cost = self.calculate_rehab_cost({})
                    down_payment = new_entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
                    loan_amount = offer_price - down_payment
                    amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
                    if amortization <= self.config["max_amortization_years"]:
                        break
                    else:
                        max_monthly_payment = loan_amount / (self.config["max_amortization_years"] * 12)
                        monthly_cash_flow = rent - non_debt_expenses - max_monthly_payment
                        break

        return monthly_cash_flow, entry_fee_percent

    def calculate_max_owner_favored_offer(self, property_data: PropertyData, repairs: Dict[str, float]) -> OfferResult:
        offer_cfg = self.config["offers"]["owner_favored"]
        appreciation_profit = property_data.listed_price * offer_cfg["appreciation_profit_percent_of_listed"]
        balloon_period = offer_cfg["balloon_period"]
        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        offer_price = appreciated_value - appreciation_profit

        rehab_cost = self.calculate_rehab_cost(repairs)

        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        if not is_buyable:
            return self._create_unbuyable_result("Max Owner Favored", unbuyable_reason, offer_price, rehab_cost,
                                                 balloon_period, appreciation_profit)

        target_cash_flow, final_entry_fee_percent = self._run_owner_adjustment_loop(offer_price, property_data)

        rent = property_data.monthly_rent
        non_debt_expenses = (property_data.monthly_property_tax + property_data.monthly_insurance +
                             property_data.monthly_hoa_fee + property_data.monthly_other_fees +
                             (rent * self.config["monthly_vacancy_rate"]) + (rent * self.config["monthly_capex_rate"]) +
                             (rent * self.config["monthly_prop_mgmt_rate"]))
        monthly_payment = rent - non_debt_expenses - target_cash_flow

        # NEW: Enforce 45-year amortization cap
        entry_fee_amount = offer_price * (final_entry_fee_percent / 100)
        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        loan_amount = offer_price - down_payment

        if monthly_payment > 0:
            amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
            if amortization > self.config["max_amortization_years"]:
                # Cap the payment and recalculate cash flow
                monthly_payment = loan_amount / (self.config["max_amortization_years"] * 12)
                target_cash_flow = rent - non_debt_expenses - monthly_payment

        return self._create_offer_result("Max Owner Favored", is_buyable, unbuyable_reason, offer_price,
                                         target_cash_flow, final_entry_fee_percent,
                                         monthly_payment, balloon_period, appreciation_profit, rehab_cost)

    def calculate_max_buyer_favored_offer(self, property_data: PropertyData, repairs: Dict[str, float]) -> OfferResult:
        offer_cfg = self.config["offers"]["buyer_favored"]
        offer_price = property_data.listed_price
        balloon_period = offer_cfg["balloon_period"]
        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        appreciation_profit = appreciated_value - offer_price

        rehab_cost = self.calculate_rehab_cost(repairs)

        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        if not is_buyable:
            return self._create_unbuyable_result("Max Buyer Favored", unbuyable_reason, offer_price, rehab_cost,
                                                 balloon_period, appreciation_profit)

        entry_fee_percent = offer_cfg["entry_fee_percent_target"]
        target_coc = offer_cfg["target_coc_percent"]

        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        initial_cash_flow = (target_coc / 100) * entry_fee_amount / 12

        rent = property_data.monthly_rent
        non_debt_expenses = (property_data.monthly_property_tax + property_data.monthly_insurance +
                             property_data.monthly_hoa_fee + property_data.monthly_other_fees +
                             (rent * self.config["monthly_vacancy_rate"]) + (rent * self.config["monthly_capex_rate"]) +
                             (rent * self.config["monthly_prop_mgmt_rate"]))
        initial_monthly_payment = rent - non_debt_expenses - initial_cash_flow

        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        loan_amount = offer_price - down_payment

        initial_amortization = self.calculate_amortization_period(loan_amount, initial_monthly_payment)

        # NEW: Always enforce 45-year amortization cap
        if initial_amortization <= self.config["max_amortization_years"]:
            final_monthly_cash_flow = initial_cash_flow
            final_monthly_payment = initial_monthly_payment
        else:
            max_amortization = self.config["max_amortization_years"]
            final_monthly_payment = loan_amount / (max_amortization * 12)
            final_monthly_cash_flow = rent - non_debt_expenses - final_monthly_payment

        return self._create_offer_result("Max Buyer Favored", is_buyable, unbuyable_reason, offer_price,
                                         final_monthly_cash_flow, entry_fee_percent,
                                         final_monthly_payment, balloon_period, appreciation_profit, rehab_cost)

    def calculate_balanced_offer(self, owner_offer: OfferResult, buyer_offer: OfferResult, property_data: PropertyData,
                                 repairs: Dict[str, float]) -> OfferResult:
        offer_cfg = self.config["offers"]["balanced"]
        offer_price = (owner_offer.final_offer_price + buyer_offer.final_offer_price) / 2
        entry_fee_percent = (owner_offer.final_entry_fee_percent + buyer_offer.final_entry_fee_percent) / 2
        balloon_period = offer_cfg["balloon_period"]

        rehab_cost = self.calculate_rehab_cost(repairs)

        is_buyable, unbuyable_reason = self.check_rehab_buyability(rehab_cost, property_data.arv, offer_price)
        appreciated_value = self.calculate_appreciated_value(property_data.listed_price, balloon_period)
        appreciation_profit = appreciated_value - offer_price
        if not is_buyable:
            return self._create_unbuyable_result("Balanced", unbuyable_reason, offer_price, rehab_cost, balloon_period,
                                                 appreciation_profit)

        target_coc = offer_cfg["target_coc_percent"]
        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        monthly_cash_flow = (target_coc / 100) * entry_fee_amount / 12

        if is_buyable and monthly_cash_flow < offer_cfg["monthly_cash_flow_min"]:
            is_buyable, unbuyable_reason = False, f"Calculated cash flow (${monthly_cash_flow:,.2f}) is below minimum of ${offer_cfg['monthly_cash_flow_min']:.2f}."

        rent = property_data.monthly_rent
        non_debt_expenses = (property_data.monthly_property_tax + property_data.monthly_insurance +
                             property_data.monthly_hoa_fee + property_data.monthly_other_fees +
                             (rent * self.config["monthly_vacancy_rate"]) + (rent * self.config["monthly_capex_rate"]) +
                             (rent * self.config["monthly_prop_mgmt_rate"]))
        monthly_payment = rent - non_debt_expenses - monthly_cash_flow

        # NEW: Enforce 45-year amortization cap
        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        loan_amount = offer_price - down_payment

        if monthly_payment > 0:
            amortization = self.calculate_amortization_period(loan_amount, monthly_payment)
            if amortization > self.config["max_amortization_years"]:
                # Cap the payment and recalculate cash flow
                monthly_payment = loan_amount / (self.config["max_amortization_years"] * 12)
                monthly_cash_flow = rent - non_debt_expenses - monthly_payment

        return self._create_offer_result("Balanced", is_buyable, unbuyable_reason, offer_price,
                                         monthly_cash_flow, entry_fee_percent,
                                         monthly_payment, balloon_period, appreciation_profit, rehab_cost)

    def _create_offer_result(self, offer_type: str, is_buyable: bool, unbuyable_reason: str,
                             offer_price: float, monthly_cash_flow: float, entry_fee_percent: float,
                             monthly_payment: float, balloon_period: int, appreciation_profit: float,
                             rehab_cost: float) -> OfferResult:

        entry_fee_amount = offer_price * (entry_fee_percent / 100)
        closing_cost = offer_price * self.config["closing_cost_percent_of_offer"]
        down_payment = entry_fee_amount - rehab_cost - closing_cost - self.config["assignment_fee"]
        dp_percent = (down_payment / offer_price) * 100 if offer_price > 0 else 0
        loan_amount = offer_price - down_payment

        coc = self.calculate_coc(monthly_cash_flow, entry_fee_amount)
        amortization = self.calculate_amortization_period(loan_amount, monthly_payment)

        # NEW: Ensure amortization never exceeds 45 years in the result
        amortization = min(amortization, self.config["max_amortization_years"])

        principal_paid = monthly_payment * 12 * balloon_period
        balloon_payment = loan_amount - principal_paid if loan_amount > principal_paid else 0.0

        if is_buyable:
            if monthly_payment <= 0: is_buyable, unbuyable_reason = False, "Monthly payment is not positive."
            if down_payment < 0: is_buyable, unbuyable_reason = False, "Down payment is negative."

        return OfferResult(offer_type, is_buyable, unbuyable_reason, offer_price, coc, monthly_cash_flow,
                           entry_fee_percent, entry_fee_amount, down_payment, dp_percent, loan_amount, monthly_payment,
                           balloon_period, appreciation_profit, rehab_cost, amortization, principal_paid,
                           balloon_payment)

    def _create_unbuyable_result(self, offer_type: str, reason: str, offer_price: float, rehab_cost: float,
                                 balloon_period: int, appreciation_profit: float) -> OfferResult:
        """Helper to return a standardized 'Unbuyable' result, ensuring all fields have a value."""
        return OfferResult(
            offer_type=offer_type,
            is_buyable=False,
            unbuyable_reason=reason,
            final_offer_price=offer_price,
            rehab_cost=rehab_cost,
            balloon_period=balloon_period,
            appreciation_profit=appreciation_profit,
            # Set all other financial metrics to 0 or empty for a failed offer
            final_coc_percent=0, final_monthly_cash_flow=0, final_entry_fee_percent=0,
            final_entry_fee_amount=0, down_payment=0, down_payment_percent=0,
            loan_amount=0, monthly_payment=0, amortization_years=0,
            principal_paid=0, balloon_payment=0
        )

    def calculate_all_offers(self, property_data: PropertyData, repairs: Dict[str, float]) -> List[OfferResult]:
        owner_offer = self.calculate_max_owner_favored_offer(property_data, repairs)
        buyer_offer = self.calculate_max_buyer_favored_offer(property_data, repairs)

        # Balanced offer depends on the other two, so we must check if they were buyable
        # If not, the balanced offer can't be calculated meaningfully.
        if not owner_offer.is_buyable or not buyer_offer.is_buyable:
            balanced_offer = self._create_unbuyable_result("Balanced", "Prerequisite offer(s) are unbuyable.", 0, 0, 0,
                                                           0)
        else:
            balanced_offer = self.calculate_balanced_offer(owner_offer, buyer_offer, property_data, repairs)

        return [owner_offer, buyer_offer, balanced_offer]


if __name__ == '__main__':
    def run_and_print_test_case(case_number: int, property_data: PropertyData, repairs: dict):
        print(f"\n--- Running Test Case #{case_number} ---")
        calculator = SellerFinanceCalculator(CONFIG)
        all_offers = calculator.calculate_all_offers(property_data, repairs)

        print("\n--- Results Comparison ---")
        for offer in all_offers:
            print(f"\n--- Offer Type: {offer.offer_type} ---")
            status = "Buyable" if offer.is_buyable else "Unbuyable"
            print(f"  Status: {status}")
            if not offer.is_buyable:
                print(f"  Reason: {offer.unbuyable_reason}")

            print(f"  Offer Price ($): {offer.final_offer_price:,.2f}")
            print(f"  Rehab Cost ($): {offer.rehab_cost:,.2f}")

            if offer.is_buyable:
                print(f"  Entry Fee (%): {offer.final_entry_fee_percent:.2f}%")
                print(f"  Entry Fee ($): {offer.final_entry_fee_amount:,.2f}")
                print(f"  Cash Flow ($): {offer.final_monthly_cash_flow:,.2f}")
                print(f"  Monthly Payment ($): {offer.monthly_payment:,.2f}")
                print(f"  COC (%): {offer.final_coc_percent:.2f}%")
                print(f"  Down Payment (%): {offer.down_payment_percent:.2f}%")
                print(f"  Down Payment ($): {offer.down_payment:,.2f}")
                print(f"  Loan Amount ($): {offer.loan_amount:,.2f}")
                print(f"  Amortization (Yrs): {offer.amortization_years:.2f}")
                print(f"  Principal Paid ($): {offer.principal_paid:,.2f}")
                print(f"  Balloon Payment ($): {offer.balloon_payment:,.2f}")


    property_2 = PropertyData(listed_price=87000, monthly_rent=1150, monthly_property_tax=95,
                              monthly_insurance=80, monthly_hoa_fee=0, monthly_other_fees=0, arv=95000)
    repairs_2 = {"light": 35, "medium": 15, "heavy": 5}
    run_and_print_test_case(2, property_2, repairs_2)