import streamlit as st
import pandas as pd
from seller_finance_calculator import SellerFinanceCalculator, PropertyData, OfferResult, CONFIG

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

# --- Main Title and Introduction ---
st.markdown('<h1 class="main-header">🏠 Seller Finance Deal Analyzer</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="highlight-text">
    <strong>Welcome to the Seller Finance Deal Analyzer!</strong><br>
    This comprehensive tool helps you evaluate potential real estate investment opportunities by calculating different 
    offer scenarios based on your property details. Enter the information below to get detailed financial analysis.
</div>
""", unsafe_allow_html=True)

# --- Input Section ---
st.markdown('<div class="input-section">', unsafe_allow_html=True)
st.markdown('<h2 class="section-header">📝 Property Details Input</h2>', unsafe_allow_html=True)

# Property Address
st.markdown("### 🏡 Property Information")
address = st.text_input(
    "Property Address",
    placeholder="e.g., 5500 Grand Lake Dr, San Antonio, TX 78244",
    help="Enter the full address of the property for your records.",
    key="property_address"
)

# Financial Details
st.markdown("### 💰 Financial Details")
with st.expander("💵 Core Financial Metrics", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Purchase & Taxes**")
        listed_price = st.number_input(
            "Listed Price ($)",
            min_value=0.0,
            value=99000.0,
            step=1000.0,
            help="The current asking price of the property.",
            key="listed_price",
            format="%.0f"
        )
        monthly_property_tax = st.number_input(
            "Monthly Property Tax ($)",
            min_value=0.0,
            value=130.0,
            step=10.0,
            help="Estimated monthly property taxes.",
            key="monthly_tax",
            format="%.0f"
        )
        monthly_hoa_fee = st.number_input(
            "Monthly HOA Fee ($)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="Monthly Homeowners Association fees, if any.",
            key="monthly_hoa",
            format="%.0f"
        )

    with col2:
        st.markdown("**Income & Insurance**")
        monthly_rent = st.number_input(
            "Monthly Rent ($)",
            min_value=0.0,
            value=1025.0,
            step=25.0,
            help="Estimated monthly rental income for the property.",
            key="monthly_rent",
            format="%.0f"
        )
        monthly_insurance = st.number_input(
            "Monthly Insurance ($)",
            min_value=0.0,
            value=95.0,
            step=10.0,
            help="Estimated monthly insurance costs.",
            key="monthly_insurance",
            format="%.0f"
        )
        monthly_other_fees = st.number_input(
            "Monthly Other Fees ($)",
            min_value=0.0,
            value=35.0,
            step=10.0,
            help="Any other recurring monthly property-related fees.",
            key="monthly_other_fees",
            format="%.0f"
        )

    with col3:
        st.markdown("**Property Value**")
        arv = st.number_input(
            "After Repair Value (ARV) ($)",
            min_value=0.0,
            value=100000.0,
            step=1000.0,
            help="The estimated value of the property after all necessary repairs and renovations are completed.",
            key="arv",
            format="%.0f"
        )

        # Quick calculation display
        if monthly_rent > 0 and arv > 0:
            pass
            # rent_to_value_ratio = (monthly_rent * 12) / arv * 100
            # st.metric(
            #     "Annual Rent-to-Value Ratio",
            #     f"{rent_to_value_ratio:.1f}%",
            #     help="Annual rent as percentage of ARV (1% rule benchmark)"
            # )

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
            step=50,
            help="Area needing light repairs (estimated $20/sqft).",
            key="sqft_light"
        )

    with col2:
        st.markdown("**Medium Rehab** 🟡")
        st.caption("~$35/sqft - Kitchen, bathroom updates")
        sqft_medium = st.number_input(
            "Medium Rehab (sqft)",
            min_value=0,
            step=50,
            help="Area needing medium repairs (estimated $35/sqft).",
            key="sqft_medium"
        )

    with col3:
        st.markdown("**Heavy Rehab** 🔴")
        st.caption("~$60/sqft - Structural, electrical, plumbing")
        sqft_heavy = st.number_input(
            "Heavy Rehab (sqft)",
            min_value=0,
            step=50,
            help="Area needing heavy repairs (estimated $60/sqft).",
            key="sqft_heavy"
        )

    # Calculate and display estimated rehab costs
    if sqft_light > 0 or sqft_medium > 0 or sqft_heavy > 0:
        estimated_rehab = (sqft_light * 20) + (sqft_medium * 35) + (sqft_heavy * 60)
        st.markdown(f"**Estimated Total Rehab Cost:** {format_currency(estimated_rehab)}")

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

st.markdown('</div>', unsafe_allow_html=True)

# --- Analysis Logic ---
if analyze_button:
    with st.spinner('🔄 Calculating offer scenarios...'):
        try:
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

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Financial Details**")
            input_metrics = {
                "Listed Price": format_currency(property_data.listed_price),
                "Monthly Rent": format_currency(property_data.monthly_rent),
                "ARV": format_currency(property_data.arv),
                "Monthly Expenses": format_currency(
                    property_data.monthly_property_tax +
                    property_data.monthly_insurance +
                    property_data.monthly_hoa_fee +
                    property_data.monthly_other_fees
                )
            }

            for key, value in input_metrics.items():
                st.metric(key, value)

        with col2:
            st.markdown("**Rehab Breakdown**")
            rehab_metrics = {
                "Light Rehab": f"{repairs['light']} sqft",
                "Medium Rehab": f"{repairs['medium']} sqft",
                "Heavy Rehab": f"{repairs['heavy']} sqft",
                "Total Est. Cost": format_currency(
                    repairs['light'] * 20 +
                    repairs['medium'] * 35 +
                    repairs['heavy'] * 60
                )
            }

            for key, value in rehab_metrics.items():
                st.metric(key, value)

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
            'background-color': '#d0d0d0',
            'border': '1px solid #dee2e6',
            'color': '#333333'
        })

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

# --- Configuration Display ---
# st.markdown("---")
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

# --- Footer ---
# st.markdown("---")
