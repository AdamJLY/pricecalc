import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Canada Coin Price Tracker", layout="centered")
st.title("Canada Coin Price Tracker")
st.markdown("##### Enter any coin or collectible (e.g., 2023 Silver Maple Leaf)")

# The text input box for users; default value is just a placeholder.
query = st.text_input(
    "Search multiple marketplaces (eBay.ca & eBay.com) for sold listings",
    "2023 Silver Maple Leaf"
)

def get_ebay_data(search_term: str, domain: str = "ca") -> pd.DataFrame:
    """
    Fetches sold listings from eBay (either 'ca' for Canada or 'com' for US/global).
    Returns a DataFrame with columns: Title, Price (CAD), Link, Date.
    """
    # Build the eBay sold-listings URL with filters for "Sold" and "Completed"
    base_url = (
        f"https://www.ebay.{domain}/sch/i.html"
        f"?_nkw={search_term.replace(' ', '+')}"
        f"&_sacat=0&LH_Sold=1&LH_Complete=1"
    )
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(base_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        # If eBay blocks us or times out, return an empty DataFrame
        return pd.DataFrame(columns=["Title", "Price (CAD)", "Link", "Date"])

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Every sold‐listing item is wrapped in <li class="s-item …"> 
    items = soup.select("li.s-item")
    data = []

    for item in items:
        # Newer eBay pages use these classes:
        title_elem = item.select_one(".s-item__title")
        price_elem = item.select_one(".s-item__price")
        link_elem = item.select_one("a.s-item__link")

        # The “date sold” used to be s-item__listingDate; now it’s often s-item__ended-date
        date_elem = item.select_one(".s-item__ended-date") or item.select_one(".s-item__listingDate")

        # Skip any “Sponsored” or placeholder items that have no real title/price
        if (
            not title_elem 
            or not price_elem 
            or not link_elem 
            or "Shop on eBay" in title_elem.text  # eBay sometimes injects this placeholder
            or "New Listing" in title_elem.text   # skip “New Listing” headers
        ):
            continue

        raw_price_text = price_elem.text.strip().replace("$", "").replace(",", "").split()[0]
        try:
            price_val = float(raw_price_text)
        except:
            continue

        data.append({
            "Title": title_elem.text.strip(),
            "Price (CAD)": price_val,
            "Link": link_elem["href"],
            "Date": date_elem.text.strip() if date_elem else "N/A"
        })

    return pd.DataFrame(data)


# When the user clicks “Search” (or simply enters text), we run the scraping logic
if st.button("Search") or query:
    with st.spinner("Parsing live data from eBay.ca and eBay.com… This may take a few seconds."):
        # Scrape eBay.ca and eBay.com for sold listings
        df_ca  = get_ebay_data(query, domain="ca")
        df_com = get_ebay_data(query, domain="com")

        # Combine both dataframes (if either is empty, concat will still work)
        combined = pd.concat([df_ca, df_com], ignore_index=True)

        # Remove exact duplicates by Title + Price + Date
        if not combined.empty:
            combined.drop_duplicates(subset=["Title", "Price (CAD)", "Date"], inplace=True)

        # Small pause just to show the spinner briefly (optional)
        time.sleep(1)

    # If nothing was scraped, show a warning
    if combined.empty:
        st.warning("No sold listings found. Try a broader or simpler keyword.")
    else:
        st.success(f"{len(combined)} sold results found across eBay.ca & eBay.com.")

        # Show all sold listings in a simple table
        st.dataframe(combined[["Title", "Price (CAD)", "Date", "Link"]], use_container_width=True)

        # Group by exact Title to form “categories” and compute stats
        grouped = combined.groupby("Title")["Price (CAD)"].agg(
            Count="count",
            **{"Average Price (CAD)": "mean"},
            **{"Lowest Price": "min"},
            **{"Highest Price": "max"}
        ).reset_index()

        # Format numeric columns as $xx.xx
        grouped["Average Price (CAD)"] = grouped["Average Price (CAD)"].map(lambda x: f"${x:.2f}")
        grouped["Lowest Price"]           = grouped["Lowest Price"].map(lambda x: f"${x:.2f}")
        grouped["Highest Price"]          = grouped["Highest Price"].map(lambda x: f"${x:.2f}")

        # Display the category breakdown table
        st.markdown("#### Category Breakdown (by exact title)")
        st.dataframe(grouped, use_container_width=True)

        # Compute overall stats once more for the entire combined set
        median_price = combined["Price (CAD)"].median()
        avg_price    = combined["Price (CAD)"].mean()
        min_price    = combined["Price (CAD)"].min()
        max_price    = combined["Price (CAD)"].max()

        st.markdown("#### Overall Stats Across All Categories")
        st.write(f"- Median price: ${median_price:.2f} CAD")
        st.write(f"- Average price: ${avg_price:.2f} CAD")
        st.write(f"- Lowest sold price: ${min_price:.2f} CAD")
        st.write(f"- Highest sold price: ${max_price:.2f} CAD")

st.markdown("---")
st.caption(
    "Minimalist live price tracker | Parsing public data from eBay.ca & eBay.com | Built with Streamlit"
)
