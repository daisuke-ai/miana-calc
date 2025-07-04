import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import requests
from datetime import datetime

# --- API Configuration ---
ZILLOW_RAPIDAPI_KEY = "cc9a304f2dmsh85c6974d7fe8eb3p141762jsn009b3487f6ef"
RENTCAST_API_KEY = "83c6f1e5a92d4c05bc1b3d72d2668ae6"

def calculate_arv(address, headers, property_details):
    """
    Calculates the After-Repair Value (ARV) using precise rehab comparable filters.
    """
    print("4. Starting ARV Calculation with Rehab Comp Filters...")
    APPRECIATION_RATE_DEFAULT, RADIUS_MILES, SQFT_TOLERANCE_FIXED, YEAR_BUILT_TOLERANCE = 0.03, 1, 500, 4

    appreciation_rate = APPRECIATION_RATE_DEFAULT
    try:
        print(" -> Getting local market appreciation rate...")
        response = requests.get("https://api.rentcast.io/v1/markets", headers=headers, params={"zipCode": property_details['zipCode'], "historyRange": 12})
        if response.ok and response.json().get('saleData', {}).get('history'):
            history, sorted_months = response.json()['saleData']['history'], sorted(response.json()['saleData']['history'].keys(), reverse=True)
            if len(sorted_months) >= 12:
                price_current, price_past = history[sorted_months[0]]['medianPrice'], history[sorted_months[11]]['medianPrice']
                if price_current and price_past and price_past > 0:
                    appreciation_rate = (price_current - price_past) / price_past
    except Exception: print(" -> Could not fetch appreciation rate. Using default.")

    try:
        print(f" -> Fetching sold comps with precise filters...")
        sqft, year_built = property_details.get('squareFootage'), property_details.get('yearBuilt')
        comps_params = { "address": address, "radius": RADIUS_MILES, "status": "Sold", "bedrooms": property_details.get('bedrooms'), "bathrooms": property_details.get('bathrooms'), "minSquareFootage": int(sqft - SQFT_TOLERANCE_FIXED) if sqft else None, "maxSquareFootage": int(sqft + SQFT_TOLERANCE_FIXED) if sqft else None, "minYearBuilt": int(year_built - YEAR_BUILT_TOLERANCE) if year_built else None, "maxYearBuilt": int(year_built + YEAR_BUILT_TOLERANCE) if year_built else None, "limit": 20 }
        comps_params = {k: v for k, v in comps_params.items() if v is not None}
        response = requests.get("https://api.rentcast.io/v1/listings/sale", headers=headers, params=comps_params)
        response.raise_for_status()
        comps = response.json()
        if not comps: print(" -> No sold comps found matching the precise criteria."); return None
        print(f" -> Found {len(comps)} sold comps.")
    except requests.exceptions.RequestException as e: print(f" -> ERROR: Could not fetch sold comps: {e}"); return None

    adjusted_prices, processed_comps, current_year = [], [], datetime.now().year
    for comp in comps:
        original_price, sale_date_str = comp.get('price'), comp.get('statusLastSeen')
        if not sale_date_str or original_price is None or original_price < 10000:
            continue

        try:
            selling_year, adjusted_price = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00')).year, original_price
            if current_year - selling_year > 0:
                adjusted_price = original_price * ((1 + appreciation_rate) ** (current_year - selling_year))
            adjusted_prices.append(adjusted_price)
            processed_comps.append({
                "address": comp.get("addressLine1"), "original_price": original_price, "sale_date": sale_date_str,
                "adjusted_price": adjusted_price, "bedrooms": comp.get('bedrooms'), "bathrooms": comp.get('bathrooms'),
                "squareFootage": comp.get('squareFootage'), "yearBuilt": comp.get('yearBuilt')
            })
        except (ValueError, TypeError): continue

    if not adjusted_prices:
        print(" -> No valid comps with realistic sale prices were found after filtering.")
        return None

    arv_estimate = sum(adjusted_prices) / len(adjusted_prices)
    print(f" -> ARV calculation successful. Estimate: ${arv_estimate:,.2f}")
    return {
        "arv_estimate": arv_estimate, "comps_used": processed_comps, "appreciation_rate": appreciation_rate,
        "filters_used": {"Radius (Miles)": RADIUS_MILES, "SQFT Tolerance": f"±{SQFT_TOLERANCE_FIXED}", "Year Built Tolerance": f"±{YEAR_BUILT_TOLERANCE}"}
    }


def gather_and_validate_data(address):
    print(f"--- Starting comprehensive data validation for: {address} ---")
    results = { "ADDRESS": None, "ZPID": None, "PROPERTY_TYPE_ZILLOW": None, "BEDROOMS": None, "BATHROOMS": None, "SQUARE_FOOTAGE_ZILLOW": None, "YEAR_BUILT_ZILLOW": None, "LISTED_PRICE_ZILLOW": None, "MONTHLY_RENT_ZILLOW": None, "MONTHLY_HOA_FEE_ZILLOW": None, "ANNUAL_INSURANCE_ZILLOW": None, "VALUE_ESTIMATE_RENTCAST_AVM": None, "MONTHLY_RENT_RENTCAST_AVM": None, "SQUARE_FOOTAGE_RENTCAST": None, "YEAR_BUILT_RENTCAST": None, "zipCode": None, "PROPERTY_TAXES_RENTCAST": [], "SALE_HISTORY_RENTCAST": [], "FEATURES_RENTCAST": {}, "OWNER_INFO_RENTCAST": {}, "OWNER_OCCUPIED_RENTCAST": None, "TAX_ASSESSMENTS_RENTCAST": [], "SQUARE_FOOTAGE": None, "YEAR_BUILT": None, "ARV_DATA": None, "errors": [] }
    zillow_headers, rentcast_headers = {"X-RapidAPI-Key": ZILLOW_RAPIDAPI_KEY, "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"}, {"X-Api-Key": RENTCAST_API_KEY}
    try:
        print("1. Contacting Zillow for listing details (/property)...")
        response = requests.get("https://zillow-com1.p.rapidapi.com/property", headers=zillow_headers, params={"address": address})
        response.raise_for_status(); zillow_data = response.json(); print("-> Zillow data received.")
        addr_info = zillow_data.get("address", {}); results.update({ "ADDRESS": f"{addr_info.get('streetAddress', '')}, {addr_info.get('city', '')}, {addr_info.get('state', '')} {addr_info.get('zipcode', '')}", "zipCode": addr_info.get('zipcode'), "ZPID": zillow_data.get("zpid"), "BEDROOMS": zillow_data.get("bedrooms"), "BATHROOMS": zillow_data.get("bathrooms"), "PROPERTY_TYPE_ZILLOW": zillow_data.get("homeType"), "LISTED_PRICE_ZILLOW": zillow_data.get("price") or zillow_data.get("zestimate"), "MONTHLY_RENT_ZILLOW": zillow_data.get("rentZestimate"), "MONTHLY_HOA_FEE_ZILLOW": zillow_data.get("monthlyHoaFee"), "ANNUAL_INSURANCE_ZILLOW": zillow_data.get("annualHomeownersInsurance"), "SQUARE_FOOTAGE_ZILLOW": zillow_data.get("livingArea"), "YEAR_BUILT_ZILLOW": zillow_data.get("yearBuilt") })
    except requests.exceptions.RequestException as e: results["errors"].append(f"Zillow /property API failed: {e}")
    try:
        print("2. Contacting RentCast for public records (/properties)...")
        response = requests.get("https://api.rentcast.io/v1/properties", headers=rentcast_headers, params={"address": address})
        response.raise_for_status(); rc_prop_data = response.json(); print("-> RentCast public records received.")
        if rc_prop_data:
            record = rc_prop_data[0]; results.update({ "SQUARE_FOOTAGE_RENTCAST": record.get('squareFootage'), "YEAR_BUILT_RENTCAST": record.get('yearBuilt'), "FEATURES_RENTCAST": record.get('features', {}), "OWNER_INFO_RENTCAST": record.get('owner', {}), "OWNER_OCCUPIED_RENTCAST": record.get('ownerOccupied') })
            if not results["zipCode"]: results["zipCode"] = record.get('zipCode')
            if record.get('propertyTaxes'): results["PROPERTY_TAXES_RENTCAST"] = sorted(record['propertyTaxes'].values(), key=lambda x: x['year'], reverse=True)
            if record.get('taxAssessments'): results["TAX_ASSESSMENTS_RENTCAST"] = sorted(record['taxAssessments'].values(), key=lambda x: x['year'], reverse=True)
            if record.get('history'): results["SALE_HISTORY_RENTCAST"] = sorted(record['history'].values(), key=lambda x: x['date'], reverse=True)
    except requests.exceptions.RequestException as e: results["errors"].append(f"RentCast /properties API failed: {e}")
    results["SQUARE_FOOTAGE"], results["YEAR_BUILT"] = results.get("SQUARE_FOOTAGE_ZILLOW") or results.get("SQUARE_FOOTAGE_RENTCAST"), results.get("YEAR_BUILT_ZILLOW") or results.get("YEAR_BUILT_RENTCAST")
    try:
        print("3. Contacting RentCast for AVM estimates...")
        rc_avm_params = {"address": address, "propertyType": results.get("PROPERTY_TYPE_ZILLOW"), "bedrooms": results.get("BEDROOMS"), "bathrooms": results.get("BATHROOMS"), "squareFootage": results.get("SQUARE_FOOTAGE")}
        rc_avm_params = {k: v for k, v in rc_avm_params.items() if v is not None}
        response_val = requests.get("https://api.rentcast.io/v1/avm/value", headers=rentcast_headers, params=rc_avm_params)
        if response_val.ok: results["VALUE_ESTIMATE_RENTCAST_AVM"] = response_val.json().get("price")
        response_rent = requests.get("https://api.rentcast.io/v1/avm/rent/long-term", headers=rentcast_headers, params=rc_avm_params)
        if response_rent.ok: results["MONTHLY_RENT_RENTCAST_AVM"] = response_rent.json().get("rent")
        print("-> RentCast AVM estimates received.")
    except requests.exceptions.RequestException as e: results["errors"].append(f"RentCast AVM APIs failed: {e}")
    arv_details = {'zipCode': results.get('zipCode'), 'bedrooms': results.get('BEDROOMS'), 'bathrooms': results.get('BATHROOMS'), 'squareFootage': results.get('SQUARE_FOOTAGE'), 'yearBuilt': results.get('YEAR_BUILT')}
    if all(arv_details.values()): results["ARV_DATA"] = calculate_arv(address, rentcast_headers, arv_details)
    else: print("-> Skipping ARV calculation due to missing property details.")
    print("--- Validation Complete ---")
    return results

def display_data_report(data):
    print("\n" + "="*85)
    print("      COMPREHENSIVE API DATA VALIDATION & COMPARISON REPORT")
    print("="*85)
    def print_field(label, value, currency=False, percent=False):
        val_str = "Not Available"
        if value is not None:
            if currency: val_str = f"${value:,.2f}"
            elif percent: val_str = f"{value:.2%}"
            else: val_str = str(value)
        print(f"{label:<35}: {val_str}")
    print("\n--- CORE PROPERTY DETAILS (Zillow vs. RentCast) ---")
    print_field("Full Address", data.get("ADDRESS"))
    print_field("Property Type (Zillow)", data.get("PROPERTY_TYPE_ZILLOW"))
    print_field("Square Footage (Zillow)", data.get("SQUARE_FOOTAGE_ZILLOW"))
    print_field("Square Footage (RentCast)", data.get("SQUARE_FOOTAGE_RENTCAST"))
    print_field("Year Built (Zillow)", data.get("YEAR_BUILT_ZILLOW"))
    print_field("Year Built (RentCast)", data.get("YEAR_BUILT_RENTCAST"))
    print("\n--- FINANCIAL ESTIMATES (Zillow vs. RentCast) ---")
    print_field("Sale/Zestimate Price (Zillow)", data.get("LISTED_PRICE_ZILLOW"), currency=True)
    print_field("Value Estimate (RentCast AVM)", data.get("VALUE_ESTIMATE_RENTCAST_AVM"), currency=True)
    print("-" * 50)
    print_field("Monthly Rent (Zillow 'Zestimate')", data.get("MONTHLY_RENT_ZILLOW"), currency=True)
    print_field("Monthly Rent (RentCast AVM)", data.get("MONTHLY_RENT_RENTCAST_AVM"), currency=True)
    arv_data = data.get("ARV_DATA")
    if arv_data:
        print("\n--- AFTER-REPAIR VALUE (ARV) ANALYSIS ---")
        print_field("Estimated ARV", arv_data.get("arv_estimate"), currency=True)
        print_field("Market Appreciation Rate Used", arv_data.get("appreciation_rate"), percent=True)
        print("\n  --- ARV Filter Criteria ---")
        for key, value in arv_data.get("filters_used", {}).items(): print(f"  - {key}: {value}")
        print("\n  --- Comps Used for ARV Calculation (Summary) ---")
        print("{:<40} | {:<15} | {:<15} | {:<15}".format("Comp Address", "Sale Date", "Original Price", "Adjusted Price"))
        print("-" * 90)
        for comp in arv_data.get("comps_used", []):
            if not comp.get('sale_date'): continue
            addr, date = (comp['address'] or "N/A")[:38], datetime.fromisoformat(comp['sale_date'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            orig_p, adj_p = f"${comp['original_price']:,.0f}", f"${comp['adjusted_price']:,.0f}"
            print(f"{addr:<40} | {date:<15} | {orig_p:<15} | {adj_p:<15}")
    print("\n--- OTHER FINANCIAL DATA ---")
    print_field("Monthly HOA Fee (from Zillow)", data.get("MONTHLY_HOA_FEE_ZILLOW"), currency=True)
    print_field("Annual Homeowners Insurance (Zillow)", data.get("ANNUAL_INSURANCE_ZILLOW"), currency=True)
    if data.get("PROPERTY_TAXES_RENTCAST"):
        print("\n--- PROPERTY TAX HISTORY (from RentCast Public Records) ---")
        print("{:<10} | {:<20} | {:<20}".format("Year", "Total Tax Paid", "Assessed Value"))
        print("-" * 60)
        assessments = {item['year']: item['value'] for item in data.get("TAX_ASSESSMENTS_RENTCAST", [])}
        for tax_item in data["PROPERTY_TAXES_RENTCAST"]:
            year, tax_paid = tax_item['year'], f"${tax_item.get('total', 0):,.2f}"
            assessment = f"${assessments.get(year, 0):,.2f}" if assessments.get(year) else "N/A"
            print(f"{year:<10} | {tax_paid:<20} | {assessment:<20}")
    if data.get("SALE_HISTORY_RENTCAST"):
        print("\n--- SALE HISTORY (from RentCast Public Records) ---")
        print("{:<15} | {:<15} | {:<15}".format("Date", "Event", "Price"))
        print("-" * 50)
        for item in data["SALE_HISTORY_RENTCAST"]:
            if not item.get('date'): continue
            date_str = datetime.fromisoformat(item['date'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            price = f"${item.get('price', 0):,}"
            print(f"{date_str:<15} | {item.get('event', 'N/A'):<15} | {price:<15}")
    print("\n--- OWNERSHIP & FEATURES (from RentCast Public Records) ---")
    owner_names = data.get("OWNER_INFO_RENTCAST", {}).get("names", ["Not Available"])
    print_field("Current Owner", ', '.join(owner_names))
    print_field("Owner Occupied", data.get("OWNER_OCCUPIED_RENTCAST"))
    print_field("Roof Type", data.get("FEATURES_RENTCAST", {}).get("roofType"))
    if data["errors"]:
        print("\n--- ERRORS ENCOUNTERED ---")
        for error in data["errors"]: print(f"- {error}")
    print("\n" + "="*85)


def display_rehab_comps_details(arv_data):
    if not arv_data or not arv_data.get("comps_used"):
        print("\nNo rehab comparables data to display for validation.")
        return
    print("\n" + "="*95)
    print("      VALIDATION: DETAILED REHAB COMPARABLES (up to 5 used in ARV)")
    print("="*95)
    comps_to_show = arv_data.get("comps_used", [])[:5]
    header = f"{'Address':<40} | {'Beds':<5} | {'Baths':<5} | {'SqFt':<7} | {'Yr Built':<8} | {'Adj. Price':<15}"
    print(header); print("-" * len(header))
    for comp in comps_to_show:
        addr = (comp.get('address') or "N/A")[:38]
        beds, baths = str(comp.get('bedrooms', 'N/A')), str(comp.get('bathrooms', 'N/A'))
        sqft, yr_built = str(comp.get('squareFootage', 'N/A')), str(comp.get('yearBuilt', 'N/A'))
        adj_price = f"${comp.get('adjusted_price', 0):,.0f}"
        print(f"{addr:<40} | {beds:<5} | {baths:<5} | {sqft:<7} | {yr_built:<8} | {adj_price:<15}")
    print("\nNote: This table shows the raw data of the comps to validate the filter logic.")

