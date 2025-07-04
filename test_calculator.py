from seller_finance_calculator import SellerFinanceCalculator, PropertyData, CONFIG

calculator = SellerFinanceCalculator(CONFIG)


def run_and_print_test_case(case_number: int, property_data: PropertyData, repairs: dict):
    print(f"\n--- Running Test Case #{case_number} ---")

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

        # Only print the full financial details if the offer is buyable
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
            print(f"  Balloon Term (Yrs): {offer.balloon_period}")
            print(f"  Principal Paid ($): {offer.principal_paid:,.2f}")
            print(f"  Balloon Payment ($): {offer.balloon_payment:,.2f}")
            print(f"  Appreciation Profit ($): {offer.appreciation_profit:,.2f}")


# --- Test Case #1 Data ---
property_1 = PropertyData(
    listed_price=87000, monthly_rent=1150, monthly_property_tax=95,
    monthly_insurance=80, monthly_hoa_fee=0, monthly_other_fees=25, arv=90000
)
repairs_1 = {"light": 300, "medium": 100, "heavy": 100}

# --- Test Case #2 Data ---
property_2 = PropertyData(
    listed_price=87000, monthly_rent=1150, monthly_property_tax=95,
    monthly_insurance=80, monthly_hoa_fee=0, monthly_other_fees=0, arv=95000
)
repairs_2 = {"light": 35, "medium": 15, "heavy": 5}

# --- Test Case #3 Data ---
property_3 = PropertyData(
    listed_price=99000, monthly_rent=1025, monthly_property_tax=130,
    monthly_insurance=95, monthly_hoa_fee=0, monthly_other_fees=35, arv=100000
)
repairs_3 = {"light": 100, "medium": 25, "heavy": 20}

# --- RUN ALL TEST CASES ---
run_and_print_test_case(1, property_1, repairs_1)
run_and_print_test_case(2, property_2, repairs_2)
run_and_print_test_case(3, property_3, repairs_3)