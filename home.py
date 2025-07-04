import streamlit as st
import pandas as pd
from seller_finance_calculator import SellerFinanceCalculator, PropertyData, OfferResult, CONFIG

# --- Page Configuration ---
st.set_page_config(
    page_title="Real Estate Offer Analysis",
    layout="wide"
)

# --- Main Title and Introduction ---
st.title("Seller Finance Deal Analyzer")
st.markdown("Welcome to the **Seller Finance Deal Analyzer**! This tool helps you evaluate potential real estate deals by calculating different offer scenarios based on your input. Enter the property details below to get started.")



# --- Input Section ---
st.header("Property Details Input")

with st.container(border=True):
    st.markdown("### General Property Information")
    address = st.text_input(
        "Property Address",
        placeholder="e.g., 5500 Grand Lake Dr, San Antonio, TX 78244",
        help="Enter the full address of the property.",
        key="property_address"
    )

    st.markdown("### Financial Details")
    with st.expander("Click to enter property financial metrics", expanded=True):
        col4, col5, col6 = st.columns(3)
        with col4:
            listed_price = st.number_input("Listed Price ($)", min_value=0.0, value=99000.0, step=1000.0, help="The current asking price of the property.", key="listed_price")
            monthly_property_tax = st.number_input("Monthly Property Tax ($)", min_value=0.0, value=130.0, step=10.0, help="Estimated monthly property taxes.", key="monthly_tax")
            monthly_hoa_fee = st.number_input("Monthly HOA Fee ($)", min_value=0.0, value=0.0, step=10.0, help="Monthly Homeowners Association fees, if any.", key="monthly_hoa")
        with col5:
            monthly_rent = st.number_input("Monthly Rent ($)", min_value=0.0, value=1025.0, step=10.0, help="Estimated monthly rental income for the property.", key="monthly_rent")
            monthly_insurance = st.number_input("Monthly Insurance ($)", min_value=0.0, value=95.0, step=10.0, help="Estimated monthly insurance costs.", key="monthly_insurance")
            monthly_other_fees = st.number_input("Monthly Other Fees ($)", min_value=0.0, value=35.0, step=10.0, help="Any other recurring monthly property-related fees.", key="monthly_other_fees")
        with col6:
            arv = st.number_input("After Repair Value (ARV) ($)", min_value=0.0, value=100000.0, step=1000.0, help="The estimated value of the property after all necessary repairs and renovations are completed.", key="arv")

    st.markdown("### Rehab Details")
    with st.expander("Click to enter estimated rehab square footage", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            sqft_light = st.number_input(
                "Light Rehab (sqft)",
                min_value=0,
                step=50,
                help="Area needing light repairs (estimated $20/sqft).",
                key="sqft_light"
            )

        with col2:
            sqft_medium = st.number_input(
                "Medium Rehab (sqft)",
                min_value=0,
                step=50,
                help="Area needing medium repairs (estimated $35/sqft).",
                key="sqft_medium"
            )

        with col3:
            sqft_heavy = st.number_input(
                "High Rehab (sqft)",
                min_value=0,
                step=50,
                help="Area needing heavy repairs (estimated $60/sqft).",
                key="sqft_heavy"
            )

    st.divider()

    col_buttons1, col_buttons2 = st.columns(2)
    with col_buttons1:
        if st.button("Analyze Property", type="primary", use_container_width=True):
            with st.spinner('Calculating offer scenarios...'):
                property_data = PropertyData(
                    listed_price=listed_price,
                    monthly_rent=monthly_rent,
                    monthly_property_tax=monthly_property_tax,
                    monthly_insurance=monthly_insurance,
                    monthly_hoa_fee=monthly_hoa_fee,
                    monthly_other_fees=monthly_other_fees,
                    arv=arv
                )
                repairs = {
                    "light": sqft_light,
                    "medium": sqft_medium,
                    "heavy": sqft_heavy
                }

                # Store inputs in session state to display later
                st.session_state['property_data'] = property_data
                st.session_state['repairs'] = repairs

                calculator = SellerFinanceCalculator(CONFIG)
                all_offers = calculator.calculate_all_offers(property_data, repairs)

                display_offer_data = {
                    "Attribute": [
                        "ARV", "Rehab Cost", "Balloon Term (Yrs)", "Offer Price", "Entry Fee (%)",
                        "Entry Fee ($)", "Monthly Cash Flow", "Monthly Payment", "COC (%)",
                        "Down Payment", "Down Payment (%)", "Amortization (Yrs)", "Principal Paid",
                        "Balloon Payment"
                    ]
                }

                for offer in all_offers:
                    col_name = ""
                    if offer.offer_type == "Max Owner Favored":
                        col_name = "Owner Favored Offer"
                    elif offer.offer_type == "Balanced":
                        col_name = "Balanced Offer"
                    elif offer.offer_type == "Max Buyer Favored":
                        col_name = "Buyer Favored Offer"

                    if offer.is_buyable:
                        display_offer_data[col_name] = [
                            f"${property_data.arv:,.0f}",  # ARV - Now directly from input
                            f"${offer.rehab_cost:,.0f}",  # Rehab Cost
                            f"{offer.balloon_period}",  # Balloon Term
                            f"${offer.final_offer_price:,.0f}",  # Offer Price
                            f"{offer.final_entry_fee_percent:.2f}%",  # Entry Fee (%)
                            f"${offer.final_entry_fee_amount:,.0f}",  # Entry Fee ($)
                            f"${offer.final_monthly_cash_flow:,.0f}",  # Monthly Cash Flow
                            f"${offer.monthly_payment:,.0f}",  # Monthly Payment
                            f"{offer.final_coc_percent:.2f}%",  # COC (%)
                            f"${offer.down_payment:,.0f}",  # Down Payment
                            f"{offer.down_payment_percent:.2f}%",  # Down Payment (%)
                            f"{offer.amortization_years:.2f}",  # Amortization
                            f"${offer.principal_paid:,.0f}",  # Principal Paid
                            f"${offer.balloon_payment:,.0f}"  # Balloon Payment
                        ]
                    else:
                        display_offer_data[col_name] = [
                            f"${property_data.arv:,.0f}",  # ARV - Always show input ARV
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Rehab Cost
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Balloon Term
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Offer Price
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Entry Fee (%)
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Entry Fee ($)
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Monthly Cash Flow
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Monthly Payment
                            f"N/A (Reason: {offer.unbuyable_reason})",  # COC (%)
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Down Payment
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Down Payment (%)
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Amortization
                            f"N/A (Reason: {offer.unbuyable_reason})",  # Principal Paid
                            f"N/A (Reason: {offer.unbuyable_reason})"  # Balloon Payment
                        ]

                offer_df = pd.DataFrame(display_offer_data)
                st.session_state['offer_df'] = offer_df

                if 'balloon_payments' in st.session_state:
                    del st.session_state['balloon_payments']

                unbuyable_offers = [offer.unbuyable_reason for offer in all_offers if not offer.is_buyable]
                if unbuyable_offers:
                    st.session_state['unbuyable_messages'] = unbuyable_offers
                else:
                    if 'unbuyable_messages' in st.session_state:
                        del st.session_state['unbuyable_messages']
    with col_buttons2:
        if st.button("Clear Inputs", type="secondary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()

    st.divider()

    # --- Recommended Values Section ---
    st.header("Recommended Values")
    st.markdown("These are the recommended values used in calculations for conservative analysis:")

    with st.expander("Show Recommended Values", expanded=True):
        st.markdown("### Conservative Values")
        st.write(f"- **Annual Interest Rate:** {CONFIG['annual_interest_rate'] * 100:.2f}%")
        st.write(f"- **Assignment Fee:** ${CONFIG['assignment_fee']:,}")
        st.write(f"- **Monthly Capex & Maintenance Rate:** {CONFIG['monthly_capex_rate'] * 100:.0f}% of Rent")
        st.write(f"- **Monthly Property Management Rate:** {CONFIG['monthly_prop_mgmt_rate'] * 100:.0f}% of Rent")
        st.write(f"- **Monthly Vacancy Rate:** {CONFIG['monthly_vacancy_rate'] * 100:.0f}% of Rent")
        st.write(f"- **Balloon Term:** {CONFIG['offers']['owner_favored']['balloon_period']}-{CONFIG['offers']['buyer_favored']['balloon_period']} years")
        st.write(f"- **Appreciation % Per Year:** {CONFIG['appreciation_per_year'] * 100:.1f}%")
        st.write(f"- **Max Amortization:** {CONFIG['max_amortization_years']} years")


st.divider()


st.header("Offer Analysis Results")
st.markdown("Here are the calculated offer scenarios based on your inputs:")

# --- Display Your Inputs ---
if 'property_data' in st.session_state and 'repairs' in st.session_state:
    st.header("Your Inputs")
    with st.container(border=True):
        property_data = st.session_state['property_data']
        repairs = st.session_state['repairs']

        input_data = {
            "Attribute": [
                "Listed Price", "Monthly Rent", "Monthly Property Tax",
                "Monthly Insurance", "Monthly HOA Fee", "Monthly Other Fees", "ARV",
                "Light Rehab (sqft)", "Medium Rehab (sqft)", "High Rehab (sqft)"
            ],
            "Your Value": [
                f"${property_data.listed_price:,.2f}",
                f"${property_data.monthly_rent:,.2f}",
                f"${property_data.monthly_property_tax:,.2f}",
                f"${property_data.monthly_insurance:,.2f}",
                f"${property_data.monthly_hoa_fee:,.2f}",
                f"${property_data.monthly_other_fees:,.2f}",
                f"${property_data.arv:,.2f}",
                f"{repairs['light']}",
                f"{repairs['medium']}",
                f"{repairs['heavy']}"
            ]
        }
        input_df = pd.DataFrame(input_data)
        st.dataframe(input_df, hide_index=True, use_container_width=True)
    st.divider()

with st.container(border=True):
    if 'unbuyable_messages' in st.session_state and st.session_state['unbuyable_messages']:
        for msg in st.session_state['unbuyable_messages']:
            st.warning(f"* **Offer Not Buyable:** {msg}")

    if 'offer_df' in st.session_state:
        st.dataframe(st.session_state['offer_df'], hide_index=True, use_container_width=True)
    else:
        st.info("Enter property details and click 'Analyze Property' to see the results.")
        pass

    st.divider()

