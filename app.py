import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Canada Coin Price Tracker", layout="centered")
st.title("Canada Coin Price Tracker")
st.markdown("##### Enter any coin or collectible (e.g., 2023 Silver Maple Leaf)")

# Input box for the user to type any coin or collectible name:
query = st.text_input(
    "Search multiple marketplaces (eBay.ca & eBay.com) for sold listings",
    "2023 Silver Maple Leaf"
)

def get_ebay_data(search_term: str, domain: str = "ca") -> pd.DataFrame:
    """
    Fetches sold listings from eBay (domain can be 'ca' for Canada or 'com' for global).
    Returns a DataFrame with columns: Title, Price (CAD), Link, Date.
    """
    base_url = (
        f"https://www.ebay.{domain}/sch/i.html"
        f"?_nkw={search_term.replace(' ', '+')}"
        f"&_sacat=0&LH_Sold=1&LH_Complete=1"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(base_url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception:
        # In case eBay blocks or times out, return empty DataFrame
        return pd.DataFrame(columns=["Title", "Price (CAD)", "Link", "Date"])
    
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.find_all("li", class_="s-item")
    data = []
    
    for item in items:
        title_elem = item.find("h3", class_="s-item__title")
        price_elem = item.find("span", class_="s-item__price")
        link_elem = item.find("a", class_="s-item__link")
        date_elem = item.find("span", class_="s-item__listingDate")
        
        if title_elem and price_elem and link_elem:
            # Try to parse the price (strip "$", commas, etc.)
            price_text = price_elem.text.strip().replace("$", "").replace(",", "").split()[0]
            try:
                price_val = float(price_text)
            except:
                continue
            
            data.append({
                "Title": title_elem.text.strip(),
                "Price (CAD)": price_val,
                "Link": link_elem["href"],
                "Date": date_elem.text.strip() if date_elem else "N/A"
            })
    
    return pd.DataFrame(data)

# When the user clicks Search (or as soon as they type a query), run:
if st.button("Search") or query:
    with st.spinner("Parsing live data from eBay.ca and eBay.com… This may take a few seconds."):
        # Fetch from both domains
        df_ca = get_ebay_data(query, domain="ca")
        df_com = get_ebay_data(query, domain="com")
        
        # Combine and drop duplicates (by Title+Price+Date—assuming identical listings appear similarly)
        combined = pd.concat([df_ca, df_com], ignore_index=True)
        if not combined.empty:
            combined.drop_duplicates(subset=["Title", "Price (CAD)", "Date"], inplace=True)
        time.sleep(1)  # optional small delay for effect

    if combined.empty:
        st.warning("No sold listings found. Try a broader or simpler keyword.")
    else:
        # Show a success message with total results:
        st.success(f"{len(combined)} total sold listings found across eBay.ca & eBay.com.")
        
        # Display all raw listings in a clean table:
        st.dataframe(combined[["Title", "Price (CAD)", "Date", "Link"]], use_container_width=True)

        # Now group by Title to get category breakdown and compute stats:
        grouped = combined.groupby("Title")["Price (CAD)"].agg(
            Count="count",
            **{"Average Price (CAD)": "mean"},
            **{"Lowest Price": "min"},
            **{"Highest Price": "max"}
        ).reset_index()

        # Format the monetary columns to two decimal places:
        grouped["Average Price (CAD)"] = grouped["Average Price (CAD)"].map(lambda x: f"${x:.2f}")
        grouped["Lowest Price"] = grouped["Lowest Price"].map(lambda x: f"${x:.2f}")
        grouped["Highest Price"] = grouped["Highest Price"].map(lambda x: f"${x:.2f}")

        # Display the grouped category stats:
        st.markdown("#### Category Breakdown (by exact title)")
        st.dataframe(grouped, use_container_width=True)

        # Overall stats:
        median_price = combined["Price (CAD)"].median()
        avg_price = combined["Price (CAD)"].mean()
        min_price = combined["Price (CAD)"].min()
        max_price = combined["Price (CAD)"].max()

        st.markdown("#### Overall Stats Across All Categories")
        st.write(f"- Median price: ${median_price:.2f} CAD")
        st.write(f"- Average price: ${avg_price:.2f} CAD")
        st.write(f"- Lowest sold price: ${min_price:.2f} CAD")
        st.write(f"- Highest sold price: ${max_price:.2f} CAD")

st.markdown("---")
st.caption(
    "Minimalist live price tracker | Parsing public data from eBay.ca & eBay.com | Built with Streamlit"
)
