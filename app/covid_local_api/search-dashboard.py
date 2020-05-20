import streamlit as st
import requests

# import pandas as pd

API_URL = "http://127.0.0.1:80"

st.title("Search for local Corona information")
"Enter your location and we will show you local hotlines, websites, test sites, health departments, and restrictions."

place_query = st.text_input("City, Neighborhood, State, ...", value="Berlin Mitte")

# Search for place with /places endpoint.
places = requests.get(f"{API_URL}/places?q={place_query}").json()

if len(places) == 0:
    "We could not find this place!"
else:
    place = places[0]
    f"Found this place: {place['name']} ({place['country']}) – Geonames ID: {place['geonames_id']}"
    st.markdown("<br/>", unsafe_allow_html=True)

    # Show a map of this place.
    # df = pd.DataFrame(
    #     [(x["lat"], x["lon"]) for x in response_json["test_sites"]],
    #     columns=["lat", "lon"],
    # )
    # df
    # st.sidebar.map(df)
    # response_json["test_sites"]

    # Fetch /all endpoint for this place.
    results = requests.get(f"{API_URL}/all?geonames_id={place['geonames_id']}").json()

    # Show results.
    "## :telephone_receiver: Hotlines"
    for hotline in results["hotlines"]:
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
    for website in results["websites"]:
        lines = [
            f"**{website['operator']}: {website['name']}**",
            f"{website['website']}",
        ]
        lines = [line for line in lines if line != "None"]
        st.markdown("<br/>".join(lines), unsafe_allow_html=True)
    st.markdown("<hr/>", unsafe_allow_html=True)

    "## :hospital: Test sites"
    # TODO: Show distance for each test site
    for test_site in results["test_sites"]:
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
    for health_department in results["health_departments"]:
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
