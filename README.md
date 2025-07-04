# Seller Finance Deal Analyzer

This Streamlit application helps real estate investors analyze potential seller finance deals by calculating various offer scenarios based on property details and conservative financial parameters.

## Features

- **Property Details Input**: Enter key financial and physical attributes of a property.
- **Rehab Cost Estimation**: Input estimated square footage for light, medium, and heavy repairs to calculate rehab costs.
- **Recommended Values Display**: View the conservative financial parameters used in the calculations.
- **Your Inputs Display**: See a summary of the values you've entered before viewing the results.
- **Offer Analysis Results**: Get a detailed breakdown of "Max Owner Favored", "Balanced", and "Max Buyer Favored" offer scenarios, including cash flow, entry fees, and more.
- **Buyability Checks**: The calculator determines if an offer is "buyable" based on predefined criteria, providing reasons if it's not.

## Getting Started

Follow these steps to set up and run the application locally.

### Prerequisites

Ensure you have Python 3.8+ installed.

### Installation

1.  Clone this repository to your local machine:
    ```bash
    git clone https://github.com/your-username/miana-calc.git
    cd miana-calc
    ```

2.  Create a virtual environment (recommended):
    ```bash
    python -m venv venv
    ```

3.  Activate the virtual environment:
    *   **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

Once the dependencies are installed, you can run the Streamlit application:

```bash
streamlit run front-end.py
```

This will open the application in your default web browser.

## Project Structure

-   `front-end.py`: The main Streamlit application script, handling user interface and displaying results.
-   `seller_finance_calculator.py`: Contains the core logic for calculating offer scenarios and financial metrics.
-   `test_calculator.py`: Unit tests for the `seller_finance_calculator.py`.
-   `README.md`: This file, providing an overview and instructions.
-   `requirements.txt`: Lists all Python dependencies required to run the application.

## Configuration (Recommended Values)

The `seller_finance_calculator.py` file contains a `CONFIG` dictionary with various parameters used in the calculations. These represent the "conservative / recommended values" and can be adjusted as needed. 