import requests
import streamlit as st
import hashlib
from .supabase_client import get_cached_data, cache_data

ZILLOW_RAPIDAPI_KEY = st.secrets["ZILLOW_RAPIDAPI_KEY"]
RENTCAST_API_KEY = st.secrets["RENTCAST_API_KEY"]
RENTOMETER_API_KEY = st.secrets["RENTOMETER_API_KEY"]

def gather_and_validate_data(address):
    print(f"--- Starting comprehensive data validation for: {address} ---")

    # Generate a consistent hash for the address
    address_hash = hashlib.sha256(address.encode('utf-8')).hexdigest()

    # Check Supabase for cached data
    cached_data = get_cached_data(address_hash)
    if cached_data:
        print(f"-> Found cached data for {address} in Supabase. Using cached data.")
        return cached_data

    results = {
        "ADDRESS": None, "ZPID": None, "PROPERTY_TYPE_ZILLOW": None,
        "BEDROOMS": None, "BATHROOMS": None,
        "LISTED_PRICE_ZILLOW": None,
        "MONTHLY_RENT_ZILLOW_COMPS": None, "MONTHLY_HOA_FEE_ZILLOW": None,
        "ANNUAL_TAX_ZILLOW": None, "ANNUAL_INSURANCE_ZILLOW": None,
        "MONTHLY_RENT_RENTCAST_AVM": None, "MONTHLY_HOA_FEE_RENTCAST": None,
        "zipCode": None, "PROPERTY_TAXES_RENTCAST": [],
        "TAX_ASSESSMENTS_RENTCAST": [],
        "MONTHLY_RENT_RENTOMETER_P25": None, "BEDROOMS_RENTCAST": None,
        "BATHROOMS_RENTCAST": None,
        "errors": [],
        "ANNUAL_TAX_FINAL_MONTHLY": None,
        "ANNUAL_INSURANCE_FINAL_MONTHLY": None
    }

    zillow_headers = {"X-RapidAPI-Key": ZILLOW_RAPIDAPI_KEY, "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"}
    rentcast_headers = {"X-Api-Key": RENTCAST_API_KEY}

    # Step 1: Get Zillow property details
    try:
        print("1a. Contacting Zillow for listing details (/property)..")
        response = requests.get("https://zillow-com1.p.rapidapi.com/property",
                                headers=zillow_headers, params={"address": address})
        response.raise_for_status()
        zillow_data = response.json()
        print("-> Zillow property data received.")

        addr_info = zillow_data.get("address", {})

        results.update({
            "ADDRESS": f"{addr_info.get('streetAddress', '')}, {addr_info.get('city', '')}, {addr_info.get('state', '')} {addr_info.get('zipcode', '')}",
            "zipCode": addr_info.get('zipcode'),
            "ZPID": zillow_data.get("zpid"),
            "BEDROOMS": zillow_data.get("bedrooms"),
            "BATHROOMS": zillow_data.get("bathrooms"),
            "PROPERTY_TYPE_ZILLOW": zillow_data.get("homeType"),
            "LISTED_PRICE_ZILLOW": zillow_data.get("price") or zillow_data.get("zestimate"),
            # VERIFIED: Correctly targets the top-level numeric value for the monthly HOA fee.
            "MONTHLY_HOA_FEE_ZILLOW": zillow_data.get("monthlyHoaFee"),
            # VERIFIED: Correctly targets the top-level numeric value for the annual tax.
            "ANNUAL_TAX_ZILLOW": zillow_data.get("taxAnnualAmount"),
            # VERIFIED: Correctly targets the top-level numeric value for the annual insurance.
            "ANNUAL_INSURANCE_ZILLOW": zillow_data.get("annualHomeownersInsurance"),
        })
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"Zillow /property API failed: {e}")

    # Step 2: Get RentCast property details
    try:
        print("2. Contacting RentCast for public records (/properties)...")
        response = requests.get("https://api.rentcast.io/v1/properties",
                                headers=rentcast_headers, params={"address": address})
        response.raise_for_status()
        rc_prop_data = response.json()
        print("-> RentCast public records received.")

        if rc_prop_data:
            record = rc_prop_data[0]
            results.update({
                "BEDROOMS_RENTCAST": record.get('bedrooms'),
                "BATHROOMS_RENTCAST": record.get('bathrooms'),
                "MONTHLY_HOA_FEE_RENTCAST": record.get('hoa', {}).get('fee') if record.get('hoa') else None
            })

            if not results["zipCode"]:
                results["zipCode"] = record.get('zipCode')

            if record.get('propertyTaxes'):
                results["PROPERTY_TAXES_RENTCAST"] = sorted(
                    record['propertyTaxes'].values(), key=lambda x: x['year'], reverse=True)
                if results["PROPERTY_TAXES_RENTCAST"]:
                    results["ANNUAL_TAX_RENTCAST_LATEST"] = results["PROPERTY_TAXES_RENTCAST"][0].get('total')

            if record.get('taxAssessments'):
                results["TAX_ASSESSMENTS_RENTCAST"] = sorted(
                    record['taxAssessments'].values(), key=lambda x: x['year'], reverse=True)
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"RentCast /properties API failed: {e}")

    # Consolidate bed/bath data (Zillow first, then RentCast fallback)
    final_bedrooms = results.get("BEDROOMS") or results.get("BEDROOMS_RENTCAST")
    final_bathrooms = results.get("BATHROOMS") or results.get("BATHROOMS_RENTCAST")
    results["BEDROOMS"] = final_bedrooms
    results["BATHROOMS"] = final_bathrooms

    # Consolidate HOA fee (Zillow first, then RentCast fallback)
    final_hoa_fee = results.get("MONTHLY_HOA_FEE_ZILLOW")
    rentcast_hoa_fee = results.get("MONTHLY_HOA_FEE_RENTCAST")

    if final_hoa_fee is not None and rentcast_hoa_fee is not None:
        results["MONTHLY_HOA_FEE_FINAL"] = min(final_hoa_fee, rentcast_hoa_fee)
    elif final_hoa_fee is not None:
        results["MONTHLY_HOA_FEE_FINAL"] = final_hoa_fee
    elif rentcast_hoa_fee is not None:
        results["MONTHLY_HOA_FEE_FINAL"] = rentcast_hoa_fee
    else:
        results["MONTHLY_HOA_FEE_FINAL"] = None

    # Consolidate annual tax and convert to monthly
    zillow_annual_tax = results.get("ANNUAL_TAX_ZILLOW")
    rentcast_annual_tax = results.get("ANNUAL_TAX_RENTCAST_LATEST")
    if zillow_annual_tax is not None and rentcast_annual_tax is not None:
        results["ANNUAL_TAX_FINAL"] = min(zillow_annual_tax, rentcast_annual_tax)
    elif zillow_annual_tax is not None:
        results["ANNUAL_TAX_FINAL"] = zillow_annual_tax
    elif rentcast_annual_tax is not None:
        results["ANNUAL_TAX_FINAL"] = rentcast_annual_tax
    else:
        results["ANNUAL_TAX_FINAL"] = None

    if results["ANNUAL_TAX_FINAL"] is not None:
        results["ANNUAL_TAX_FINAL_MONTHLY"] = results["ANNUAL_TAX_FINAL"] / 12
    else:
        results["ANNUAL_TAX_FINAL_MONTHLY"] = None

    # Convert annual insurance to monthly
    if results.get("ANNUAL_INSURANCE_ZILLOW") is not None:
        results["ANNUAL_INSURANCE_FINAL_MONTHLY"] = results["ANNUAL_INSURANCE_ZILLOW"] / 12

    # Step 3: Get Zillow rent estimate (fixed endpoint)
    try:
        print("3. Contacting Zillow for rent estimate (/rentEstimate)...")

        property_type_mapping = {
            "SINGLE_FAMILY": "SingleFamily", "TOWNHOUSE": "Townhouse", "CONDO": "Condo",
            "APARTMENT": "Apartment", "MULTI_FAMILY": "MultiFamily"
        }
        mapped_property_type = property_type_mapping.get(results.get("PROPERTY_TYPE_ZILLOW"), "SingleFamily")

        rent_params = {
            "address": address, "propertyType": mapped_property_type,
            "beds": final_bedrooms, "baths": final_bathrooms
        }
        rent_params = {k: v for k, v in rent_params.items() if v is not None}

        response = requests.get("https://zillow-com1.p.rapidapi.com/rentEstimate",
                                headers=zillow_headers, params=rent_params)
        response.raise_for_status()
        rent_data = response.json()

        if "body" in rent_data:
            results["MONTHLY_RENT_ZILLOW_COMPS"] = rent_data["body"].get("percentile_25")
        else:
            results["MONTHLY_RENT_ZILLOW_COMPS"] = rent_data.get("percentile_25")

        print("-> Zillow rent estimate (25th percentile) received.")
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"Zillow /rentEstimate API failed: {e}")

    # Step 4: Get RentCast rent estimate (AVM)
    try:
        print("4. Contacting RentCast for rent AVM...")
        rc_avm_params = {
            "address": address, "propertyType": results.get("PROPERTY_TYPE_ZILLOW"),
            "bedrooms": final_bedrooms, "bathrooms": final_bathrooms,
        }
        rc_avm_params = {k: v for k, v in rc_avm_params.items() if v is not None}

        response_rent = requests.get("https://api.rentcast.io/v1/avm/rent/long-term",
                                     headers=rentcast_headers, params=rc_avm_params)
        if response_rent.ok:
            results["MONTHLY_RENT_RENTCAST_AVM"] = response_rent.json().get("rent")
            print("-> RentCast rent AVM received.")
        else:
            results["errors"].append(f"RentCast rent AVM failed: {response_rent.status_code}")
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"RentCast rent AVM failed: {e}")

    # Step 5: Get Rentometer rent estimate
    try:
        print("5. Contacting Rentometer for statistical rent summary...")
        rentometer_params = {"api_key": RENTOMETER_API_KEY, "address": address, "bedrooms": final_bedrooms}

        prop_type = results.get("PROPERTY_TYPE_ZILLOW")
        if prop_type in ("SINGLE_FAMILY", "TOWNHOUSE"):
            rentometer_params["building_type"] = "house"
        elif prop_type in ("CONDO", "APARTMENT", "MULTI_FAMILY"):
            rentometer_params["building_type"] = "apartment"

        if final_bathrooms:
            if final_bathrooms == 1:
                rentometer_params["baths"] = "1"
            elif final_bathrooms >= 1.5:
                rentometer_params["baths"] = "1.5+"

        rentometer_params = {k: v for k, v in rentometer_params.items() if v is not None}

        response = requests.get("https://www.rentometer.com/api/v1/summary", params=rentometer_params)
        response.raise_for_status()
        rentometer_data = response.json()
        results["MONTHLY_RENT_RENTOMETER_P25"] = rentometer_data.get("percentile_25")
        print("-> Rentometer summary received.")
    except requests.exceptions.RequestException as e:
        results["errors"].append(f"Rentometer /summary API failed: {e}")

    # Calculate final monthly rent as the average of the three sources if available
    rent_values = [
        results.get("MONTHLY_RENT_ZILLOW_COMPS"),
        results.get("MONTHLY_RENT_RENTCAST_AVM"),
        results.get("MONTHLY_RENT_RENTOMETER_P25")
    ]
    rent_values = [v for v in rent_values if v is not None]
    if rent_values:
        results["MONTHLY_RENT_FINAL"] = sum(rent_values) / len(rent_values)
    else:
        results["MONTHLY_RENT_FINAL"] = None

    print("--- Data Gathering Complete ---")
    cache_data(address_hash, results)
    return results

def display_data_report(data):
    st.subheader("Comprehensive Data Report")

    def print_field(label, value, currency=False, percent=False):
        if value is not None:
            if currency:
                st.write(f"- **{label}:** ${value:,.2f}")
            elif percent:
                st.write(f"- **{label}:** {value:.2f}%")
            else:
                st.write(f"- **{label}:** {value}")
        else:
            st.write(f"- **{label}:** N/A")

    st.write("---")
    st.write("**Address Information:**")
    print_field("Address", data.get("ADDRESS"))
    print_field("ZPID", data.get("ZPID"))
    print_field("Property Type (Zillow)", data.get("PROPERTY_TYPE_ZILLOW"))
    print_field("Bedrooms", data.get("BEDROOMS"))
    print_field("Bathrooms", data.get("BATHROOMS"))
    st.write("---")

    st.write("**Financial Data - Raw (from APIs):**")
    print_field("Zillow Listed Price / Zestimate", data.get("LISTED_PRICE_ZILLOW"), currency=True)
    print_field("Zillow Monthly HOA Fee", data.get("MONTHLY_HOA_FEE_ZILLOW"), currency=True)
    print_field("Zillow Annual Tax", data.get("ANNUAL_TAX_ZILLOW"), currency=True)
    print_field("Zillow Annual Insurance", data.get("ANNUAL_INSURANCE_ZILLOW"), currency=True)
    print_field("RentCast Monthly HOA Fee", data.get("MONTHLY_HOA_FEE_RENTCAST"), currency=True)
    print_field("RentCast Latest Annual Tax", data.get("ANNUAL_TAX_RENTCAST_LATEST"), currency=True)
    print_field("Zillow Monthly Rent Comps (P25)", data.get("MONTHLY_RENT_ZILLOW_COMPS"), currency=True)
    print_field("RentCast Monthly Rent AVM", data.get("MONTHLY_RENT_RENTCAST_AVM"), currency=True)
    print_field("Rentometer Monthly Rent (P25)", data.get("MONTHLY_RENT_RENTOMETER_P25"), currency=True)
    st.write("---")

    st.write("**Financial Data - Consolidated & Monthly:**")
    print_field("Final Monthly Rent", data.get("MONTHLY_RENT_FINAL"), currency=True)
    print_field("Final Monthly HOA Fee", data.get("MONTHLY_HOA_FEE_FINAL"), currency=True)
    print_field("Final Monthly Property Tax", data.get("ANNUAL_TAX_FINAL_MONTHLY"), currency=True)
    print_field("Final Monthly Insurance", data.get("ANNUAL_INSURANCE_FINAL_MONTHLY"), currency=True)
    st.write("---")

    if data.get("errors"):
        st.error("--- API Errors Encountered ---")
        for error in data["errors"]:
            st.write(f"- {error}")
        st.write("---")

    if data.get("PROPERTY_TAXES_RENTCAST"):
        st.write("**RentCast Property Tax History:**")
        for tax in data["PROPERTY_TAXES_RENTCAST"]:
            st.write(f"- {tax['year']}: Assessed Value ${tax.get('assessedValue', 0):,.2f}, Total Tax ${tax.get('total', 0):,.2f}")
    if data.get("TAX_ASSESSMENTS_RENTCAST"):
        st.write("**RentCast Tax Assessments History:**")
        for assessment in data["TAX_ASSESSMENTS_RENTCAST"]:
            st.write(f"- {assessment['year']}: Assessed Value ${assessment.get('assessedValue', 0):,.2f}, Land Value ${assessment.get('landValue', 0):,.2f}, Improvements Value ${assessment.get('improvementsValue', 0):,.2f}")

def main():
    st.title("Property Data Gatherer")
    st.write("Enter an address to retrieve comprehensive property and rental data from various APIs.")

    address = st.text_input("Enter Property Address (e.g., 123 Main St, Anytown, CA 90210):")

    if st.button("Gather Data"):
        if address:
            with st.spinner("Gathering data... This may take a moment."):
                property_data = gather_and_validate_data(address)
            if property_data:
                display_data_report(property_data)
        else:
            st.warning("Please enter an address.")

if __name__ == '__main__':
    main() 