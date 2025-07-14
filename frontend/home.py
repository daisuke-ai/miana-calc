import sys
import os

import streamlit as st
import pandas as pd
from backend.logic.seller_finance_calculator import SellerFinanceCalculator, PropertyData, OfferResult, CONFIG
from backend.api.external_api_integrations import gather_and_validate_data

# --- Page Configuration ---
st.set_page_config(
    page_title="Real Estate Offer Analysis",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Better Styling ---
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: bold;
        margin-bottom: 2rem;
    }

    .section-header {
        color: #1f77b4;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }

    .warning-card {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .success-card {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .input-section {
        background: transparent;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }

    .results-section {
        background: transparent;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .highlight-text {
        background-color: transparent;
        padding: 0.5rem;
        border-radius: 4px;
        border-left: 4px solid #2196f3;
    }

    .small-text {
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def clear_all_inputs():
    """Clear all session state variables"""
    keys_to_clear = [
        'property_address', 'listed_price', 'monthly_tax', 'monthly_hoa',
        'monthly_rent', 'monthly_insurance', 'monthly_other_fees', 'arv',
        'sqft_light', 'sqft_medium', 'sqft_heavy', 'property_data', 'repairs',
        'offer_df', 'unbuyable_messages', 'balloon_payments', 'analysis_complete'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def format_currency(value):
    """Format currency with proper commas and dollar sign"""
    return f"${value:,.0f}"


def format_percentage(value):
    """Format percentage with two decimal places"""
    return f"{value:.2f}%"


# --- Initialize Session State ---
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'api_data_fetched' not in st.session_state:
    st.session_state.api_data_fetched = False

# --- Main Title and Introduction ---
st.markdown('<h1 class="main-header">🏠 Seller Finance Deal Analyzer</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="highlight-text">
    <strong>Welcome to the Seller Finance Deal Analyzer!</strong><br>
    This comprehensive tool helps you evaluate potential real estate investment opportunities by calculating different 
    offer scenarios based on your property details. Enter the information below to get detailed financial analysis.
</div>
""", unsafe_allow_html=True)

# --- Address Bar Only (Initial State) ---
st.markdown('<div class="input-section">', unsafe_allow_html=True)
st.markdown('<h2 class="section-header">📝 Property Details Input</h2>', unsafe_allow_html=True)

address = st.text_input(
    "Property Address",
    placeholder="e.g., 5500 Grand Lake Dr, San Antonio, TX 78244",
    help="Enter the full address of the property for your records.",
    key="property_address"
)

fetch_btn = st.button("Fetch Property Data", key="fetch_api_data")

if fetch_btn and address:
    with st.spinner('Fetching property data from APIs...'):
        api_data = gather_and_validate_data(address)
        st.session_state.api_data = api_data
        st.session_state.api_data_fetched = True
        # Store fetched values in separate session state keys
        st.session_state["fetched_listed_price"] = float(api_data.get("LISTED_PRICE_ZILLOW") or 0.0)
        st.session_state["fetched_monthly_rent"] = float(api_data.get("MONTHLY_RENT_FINAL") or 0.0) # This will be the initial avg
        st.session_state["fetched_monthly_tax"] = float(api_data.get("ANNUAL_TAX_FINAL_MONTHLY") or 0.0)
        st.session_state["fetched_monthly_insurance"] = float(api_data.get("ANNUAL_INSURANCE_FINAL_MONTHLY") or 0.0)
        st.session_state["fetched_monthly_hoa"] = float(api_data.get("MONTHLY_HOA_FEE_FINAL") or 0.0)
        st.session_state["fetched_arv"] = 0.0
        st.session_state["fetched_monthly_rent_zillow"] = float(api_data.get("MONTHLY_RENT_ZILLOW_COMPS") or 0.0)
        st.session_state["fetched_monthly_rent_rentcast"] = float(api_data.get("MONTHLY_RENT_RENTCAST_AVM") or 0.0)
        st.session_state["fetched_monthly_rent_rentometer"] = float(api_data.get("MONTHLY_RENT_RENTOMETER_P25") or 0.0)

st.markdown('</div>', unsafe_allow_html=True) # This closes the initial input-section

# Only show the rest of the UI if data has been fetched
if st.session_state.get('api_data_fetched', False):
    # --- Financial Details ---
    st.markdown("### 💰 Financial Details")
    with st.expander("💵 Core Financial Metrics", expanded=True):
        col1, col2, col3 = st.columns(3) # Changed from 4 columns to 3
        with col1:
            st.markdown("**Purchase & Taxes**")
            listed_price = st.number_input(
                "Listed Price ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_listed_price", 0.0)),
                step=1000.0,
                help="The current asking price of the property.",
                key="listed_price",
                format="%.0f"
            )
            monthly_property_tax = st.number_input(
                "Monthly Property Tax ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_tax", 0.0)),
                step=10.0,
                help="Estimated monthly property taxes.",
                key="monthly_tax",
                format="%.0f"
            )
            monthly_hoa_fee = st.number_input(
                "Monthly HOA Fee ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_hoa", 0.0)),
                step=10.0,
                help="Monthly Homeowners Association fees, if any.",
                key="monthly_hoa",
                format="%.0f"
            )
        with col2:
            st.markdown("**Income, Insurance & Property Value**") # Renamed column header
            monthly_insurance = st.number_input(
                "Monthly Insurance ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_insurance", 0.0)),
                step=10.0,
                help="Estimated monthly insurance costs.",
                key="monthly_insurance",
                format="%.0f"
            )
            monthly_other_fees = st.number_input(
                "Monthly Other Fees ($)",
                min_value=0.0,
                value=float(st.session_state.get("monthly_other_fees", 0.0)),
                step=10.0,
                help="Any other recurring monthly property-related fees.",
                key="monthly_other_fees",
                format="%.0f"
            )
            arv = st.number_input(
                "After Repair Value (ARV) ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_arv", 0.0)),
                step=1000.0,
                help="The estimated value of the property after all necessary repairs and renovations are completed.",
                key="arv",
                format="%.0f"
            )
        with col3:
            st.markdown("### 💸 Rent Estimates")
            rent_1 = st.number_input(
                "Rentometer 25th Percentile ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_rent_rentometer", 0.0)),
                step=25.0,
                help="Rent estimate from Rentometer (25th percentile).",
                key="rent_1",
                format="%.0f"
            )
            rent_2 = st.number_input(
                "Zillow Comps Rent ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_rent_zillow", 0.0)),
                step=25.0,
                help="Rent estimate from Zillow Comps.",
                key="rent_2",
                format="%.0f"
            )
            rent_3 = st.number_input(
                "RentCast AVM Rent ($)",
                min_value=0.0,
                value=float(st.session_state.get("fetched_monthly_rent_rentcast", 0.0)),
                step=25.0,
                help="Rent estimate from RentCast AVM.",
                key="rent_3",
                format="%.0f"
            )
            rent_4 = st.number_input(
                "User Provided Rent ($)",
                min_value=0.0,
                value=0.0, # Default to 0, user can input
                step=25.0,
                help="Enter an additional rent value if desired.",
                key="rent_4",
                format="%.0f"
            )
            # Calculate monthly_rent AFTER all inputs are defined and accessible within the expander
            rent_values = [rent_1, rent_2, rent_3, rent_4]
            valid_rent_values = [val for val in rent_values if val > 0]

            monthly_rent = 0.0 # Initialize monthly_rent here
            if valid_rent_values:
                monthly_rent = sum(valid_rent_values) / len(valid_rent_values)

            st.markdown(f"**Average Monthly Rent (Used in Calculation): {format_currency(monthly_rent)}**")

            # Perform the check after monthly_rent and arv are defined
            if monthly_rent > 0 and arv > 0:
                pass

    # Rehab Details
    st.markdown("### 🔨 Rehabilitation Estimates")
    with st.expander("🏗️ Rehab Square Footage by Intensity", expanded=True):
        st.markdown("**Estimate the square footage that needs different levels of rehabilitation:**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Light Rehab** 🟢")
            st.caption("~$20/sqft - Paint, flooring, fixtures")
            sqft_light = st.number_input(
                "Light Rehab (sqft)",
                min_value=0,
                step=10,
                help="Area needing light repairs (estimated $20/sqft).",
                key="sqft_light"
            )

        with col2:
            st.markdown("**Medium Rehab** 🟡")
            st.caption("~$35/sqft - Kitchen, bathroom updates")
            sqft_medium = st.number_input(
                "Medium Rehab (sqft)",
                min_value=0,
                step=10,
                help="Area needing medium repairs (estimated $35/sqft).",
                key="sqft_medium"
            )

        with col3:
            st.markdown("**Heavy Rehab** 🔴")
            st.caption("~$60/sqft - Structural, electrical, plumbing")
            sqft_heavy = st.number_input(
                "Heavy Rehab (sqft)",
                min_value=0,
                step=10,
                help="Area needing heavy repairs (estimated $60/sqft).",
                key="sqft_heavy"
            )

        # Calculate and display estimated rehab costs
        if sqft_light > 0 or sqft_medium > 0 or sqft_heavy > 0:
            estimated_rehab = (sqft_light * 20) + (sqft_medium * 35) + (sqft_heavy * 60)
            st.markdown(f"**Estimated Total Rehab Cost:** {format_currency(estimated_rehab)}")

    # --- Configuration Display ---
    st.markdown('<h2 class="section-header">⚙️ Analysis Configuration</h2>', unsafe_allow_html=True)

    with st.expander("📊 View Calculation Parameters", expanded=False):
        st.markdown("**These conservative values are used in all calculations:**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Financial Parameters**")
            st.write(f"• **Interest Rate:** {CONFIG['annual_interest_rate'] * 100:.2f}%")
            st.write(f"• **Assignment Fee:** {format_currency(CONFIG['assignment_fee'])}")
            st.write(f"• **Appreciation Rate:** {CONFIG['appreciation_per_year'] * 100:.1f}% annually")
            st.write(f"• **Max Amortization:** {CONFIG['max_amortization_years']} years")

        with col2:
            st.markdown("**Monthly Expense Rates**")
            st.write(f"• **CapEx & Maintenance:** {CONFIG['monthly_capex_rate'] * 100:.0f}% of rent")
            st.write(f"• **Property Management:** {CONFIG['monthly_prop_mgmt_rate'] * 100:.0f}% of rent")
            st.write(f"• **Vacancy Reserve:** {CONFIG['monthly_vacancy_rate'] * 100:.0f}% of rent")
            st.write(
                f"• **Balloon Terms:** {CONFIG['offers']['owner_favored']['balloon_period']}-{CONFIG['offers']['buyer_favored']['balloon_period']} years")

    # Action Buttons
    st.markdown("### 🚀 Analysis Actions")
    col1, col2 = st.columns([2, 1])

    with col1:
        analyze_button = st.button(
            "🔍 Analyze Property",
            type="primary",
            use_container_width=True,
            help="Calculate all offer scenarios based on your inputs"
        )

    with col2:
        if st.button("🗑️ Clear All Inputs", type="secondary", use_container_width=True):
            clear_all_inputs()
            st.rerun()

    # This closes the initial input-section wrapper
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Analysis Logic ---
    if analyze_button:
        with st.spinner('🔄 Calculating offer scenarios...'):
            try:
                property_data = PropertyData(
                    listed_price=listed_price,
                    monthly_rent=monthly_rent, # This now uses the calculated average
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

                # Store inputs in session state
                st.session_state['property_data'] = property_data
                st.session_state['repairs'] = repairs
                st.session_state['analysis_complete'] = True

                calculator = SellerFinanceCalculator(CONFIG)
                all_offers = calculator.calculate_all_offers(property_data, repairs)

                # Build display data
                display_offer_data = {
                    "Metric": [
                        "ARV", "Rehab Cost", "Balloon Term (Years)",
                        "Offer Price", "Entry Fee (%)", "Entry Fee ($)",
                        "Monthly Cash Flow", "Monthly Payment", "COC (%)",
                        "Down Payment", "Down Payment (%)", "Amortization (Years)",
                        "Principal Paid", "Balloon Payment"
                    ]
                }

                for offer in all_offers:
                    col_name = {
                        "Max Owner Favored": "Owner Favored",
                        "Balanced": "Balanced Offer",
                        "Max Buyer Favored": "Buyer Favored"
                    }.get(offer.offer_type, offer.offer_type)

                    if offer.is_buyable:
                        display_offer_data[col_name] = [
                            format_currency(property_data.arv),
                            format_currency(offer.rehab_cost),
                            f"{offer.balloon_period} years",
                            format_currency(offer.final_offer_price),
                            format_percentage(offer.final_entry_fee_percent),
                            format_currency(offer.final_entry_fee_amount),
                            format_currency(offer.final_monthly_cash_flow),
                            format_currency(offer.monthly_payment),
                            format_percentage(offer.final_coc_percent),
                            format_currency(offer.down_payment),
                            format_percentage(offer.down_payment_percent),
                            f"{offer.amortization_years:.1f} years",
                            format_currency(offer.principal_paid),
                            format_currency(offer.balloon_payment)
                        ]
                    else:
                        display_offer_data[col_name] = [
                            format_currency(property_data.arv),
                            *[f"❌ {offer.unbuyable_reason}" for _ in range(13)]
                        ]

                offer_df = pd.DataFrame(display_offer_data)
                st.session_state['offer_df'] = offer_df

                # Handle unbuyable offers
                unbuyable_offers = [offer.unbuyable_reason for offer in all_offers if not offer.is_buyable]
                if unbuyable_offers:
                    st.session_state['unbuyable_messages'] = unbuyable_offers
                else:
                    st.session_state.pop('unbuyable_messages', None)

                st.success("✅ Analysis completed successfully!")

            except Exception as e:
                st.error(f"❌ Error during analysis: {str(e)}")



    # --- Results Section ---
    # st.markdown("---")
    st.markdown('<div class="results-section">', unsafe_allow_html=True)

    if st.session_state.analysis_complete:
        st.markdown('<h2 class="section-header">📊 Analysis Results</h2>', unsafe_allow_html=True)

        # Display Input Summary
        if 'property_data' in st.session_state and 'repairs' in st.session_state:
            st.markdown("### 📋 Input Summary")
            property_data = st.session_state['property_data']
            repairs = st.session_state['repairs']

            input_summary_data = {
                "Metric": [
                    "Listed Price",
                    "Monthly Rent",
                    "ARV",
                    "Monthly Expenses",
                    "Light Rehab (sqft)",
                    "Medium Rehab (sqft)",
                    "Heavy Rehab (sqft)",
                    "Total Estimated Rehab Cost"
                ],
                "Value": [
                    format_currency(property_data.listed_price),
                    format_currency(property_data.monthly_rent),
                    format_currency(property_data.arv),
                    format_currency(
                        property_data.monthly_property_tax +
                        property_data.monthly_insurance +
                        property_data.monthly_hoa_fee +
                        property_data.monthly_other_fees
                    ),
                    f"{repairs['light']} sqft",
                    f"{repairs['medium']} sqft",
                    f"{repairs['heavy']} sqft",
                    format_currency(
                        repairs['light'] * 20 +
                        repairs['medium'] * 35 +
                        repairs['heavy'] * 60
                    )
                ]
            }
            input_summary_df = pd.DataFrame(input_summary_data)

            st.dataframe(
                input_summary_df.style.set_properties(**{
                    'background-color': '#152238',
                    'color': '#FFFFFF',
                    'border-color': '#c0c0c0'
                }),
                hide_index=True,
                use_container_width=True
            )

        # Display Warnings
        if 'unbuyable_messages' in st.session_state and st.session_state['unbuyable_messages']:
            st.markdown("### ⚠️ Investment Warnings")
            for msg in st.session_state['unbuyable_messages']:
                st.warning(f"**Not Recommended:** {msg}")

        # Display Offer Analysis
        if 'offer_df' in st.session_state:
            st.markdown("### 🎯 Offer Scenarios")
            st.markdown("Compare different offer strategies based on your investment goals:")

            # Style the dataframe
            styled_df = st.session_state['offer_df'].style.set_properties(**{
                'background-color': '#152238',  # Dark Blue/Navy
                'color': '#F0F0F0',  # Off-white
                'border': '1px solid #34495E', # Slightly lighter dark blue for border
                'font-weight': 'bold' # Make text bold for better readability on dark background
            }).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#1A242F'), ('color', '#FFFFFF')]}
            ])

            st.dataframe(
                styled_df,
                hide_index=True,
                use_container_width=True,
                height=500
            )

            # Add explanation
            st.markdown("""
            **Scenario Explanations:**
            - **Owner Favored:** Best terms for the seller, higher payments
            - **Balanced:** Compromise between buyer and seller interests  
            - **Buyer Favored:** Best terms for the buyer, lower payments
            """)

    else:
        st.markdown('<h2 class="section-header">🎯 Ready to Analyze</h2>', unsafe_allow_html=True)
        st.info("👆 Enter your property details above and click 'Analyze Property' to see comprehensive offer scenarios.")

    st.markdown('</div>', unsafe_allow_html=True)

