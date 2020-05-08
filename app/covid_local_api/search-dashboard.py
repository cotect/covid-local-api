import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:80"

st.title("Search for local Corona information")
"Enter your location and we will show you local hotlines, websites, test sites, health departments, and restrictions."

place_query = st.text_input("City, Neighborhood, State, ...", value="Berlin Mitte")

# Search for location through places service.
places_response = requests.get(f"{API_URL}/geonames?q={place_query}")
places_response_json = places_response.json()

if len(places_response_json["geonames"]) == 0:
    "We could not find this place!"
else:
    geonames_id = places_response_json["geonames"][0]["geonameId"]
    f"Found this place: {places_response_json['geonames'][0]['name']} ({places_response_json['geonames'][0]['countryName']}) – Geonames ID: {geonames_id}"

    # Show a map of this place.

    # Fetch /all endpoint for this location.

    response = requests.get(f"{API_URL}/all?geonames_id={geonames_id}")
    response_json = response.json()

    df = pd.DataFrame(
        [(x["lat"], x["lon"]) for x in response_json["test_sites"]],
        columns=["lat", "lon"],
    )
    # df

    # st.sidebar.map(df)
    # response_json["test_sites"]

    st.markdown("<br/>", unsafe_allow_html=True)

    # Show results.
    "## :telephone_receiver: Hotlines"
    for hotline in response_json["hotlines"]:
        if hotline["name"] is not None:
            title = f"**{hotline['operator']}: {hotline['name']}**"
        else:
            title = f"**{hotline['operator']}**"
        lines = [
            title,
            f"{hotline['operating_hours']}",
            f"{hotline['phone']}",
            f"{hotline['email']}",
            f"{hotline['website']}",
        ]
        lines = [line for line in lines if line != "None"]
        st.markdown("<br/>".join(lines), unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    "## :globe_with_meridians: Websites"
    for website in response_json["websites"]:
        lines = [
            f"**{website['operator']}: {website['name']}**",
            f"{website['website']}",
        ]
        lines = [line for line in lines if line != "None"]
        st.markdown("<br/>".join(lines), unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    "## :hospital: Test sites"
    # TODO: Show distance for each test site
    for test_site in response_json["test_sites"]:
        lines = [
            f"**{test_site['name']}**",
            f"{test_site['operating_hours']}",
            f"{test_site['street']}",
            f"{test_site['address_supplement']}",
            f"{test_site['zip_code']} {test_site['city']}",
            f"{test_site['phone']}",
            f"{test_site['website']}",
        ]
        lines = [line for line in lines if line != "None"]
        st.markdown("<br/>".join(lines), unsafe_allow_html=True)
    # TODO: Button with Show More

    st.markdown("<hr/>", unsafe_allow_html=True)

    "## :office: Health departments"
    for health_department in response_json["health_departments"]:
        lines = [
            f"**{health_department['name']}: {health_department['department']}**",
            f"{health_department['street']}",
            f"{health_department['address_supplement']}",
            f"{health_department['zip_code']} {health_department['city']}",
            f"{health_department['phone']}",
            f"{health_department['fax']}",
            f"{health_department['email']}",
            f"{health_department['website']}",
        ]
        lines = [line for line in lines if line != "None"]
        st.markdown("<br/>".join(lines), unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    "## :cop: Restrictions"
    "Coming soon..."
    # for regulation in response_json["regulations"]:
    # regulation
