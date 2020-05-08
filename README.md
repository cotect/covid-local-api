# covid-local-api

![](docs/images/github-banner.png)

REST API for location-based information about COVID-19 / Coronavirus (hotlines, test sites, health departments, ...). 


## What is this good for?

Websites and apps can significantly help people in the Corona crisis – by tracing contacts, checking symptoms, or providing targeted information. However, actual help in case of an infection or other problems is often local: Cities have their own hotlines; test sites and health departments are distributed across the country; and restrictions vary from region to region. We want to bridge this gap between digital tools and local help by providing an API with  information based on the user's location (hotlines, websites, test sites, health departments, restrictions). Developers can integrate this information into their tools in order to show people the best offers for local help.


## Live version

The API is now live! For a demo, head over to: [http://ec2-3-90-67-33.compute-1.amazonaws.com/all?geonames_id=6545310](http://ec2-3-90-67-33.compute-1.amazonaws.com/all?geonames_id=6545310)

This will return all local information for Berlin Mitte as a JSON. (Note that the server URL will change regularly at this stage).

We also built a small [dashboard](http://ec2-3-90-67-33.compute-1.amazonaws.com) to search through our data. 


## Local deployment 

To run the API locally, clone this repo and run the following command to start the API server locally:

    cd ./covid-local-api/app/covid_local_api
    uvicorn local_test:app --reload

The API should now be accessible at 127.0.0.1:8000.


## Endpoints

Five endpoints to get information:

- `/all`: General endpoint for all information (hotlines, websites, test sites and health departments)
- `/hotlines`: Phone hotlines for the location and any superior areas (e.g. states, countries)
- `/websites`: Information websites for the location and any superior areas (e.g. states, countries)
- `/health_departments`: Health deparments responsible for this location
- `/test_sites`: Nearby test sites, selected and sorted by distance to the location

One additional endpoint to search for locations (see also below):

- `/geonames`: Wrapper around the [geonames.org location search](http://www.geonames.org/export/geonames-search.html) with sensible defaults. Returns locations based on a query string. Use like `/geonames?q=<city, postal code, ...>`.


## Location search

For all endpoints, you indicate the location via query parameters (i.e. `?key=value` after the endpoint). The API offers three ways to search for a location:

- `?placename=<city, area, ...>`: Coming soon
- `?postalcode=<number>`: Coming soon
- `?geonames_id=<id>`: ID for a location on [geonames.org](geonames.org).org. You can retrieve the ID manually by searching on [geonames.org](geonames.org) (the ID is the number in the blue box on the right hand side of the search result view), or by using [their API](http://www.geonames.org/export/web-services.html). To make things easier, we offer a wrapper around their [location search](http://www.geonames.org/export/geonames-search.html) at the `/geonames` endpoint (see above). 


## Output

All endpoints return a JSON in the format:

    {
        "hotlines": [...],
        "websites": [...],
        "health_deparments": [...],
        "test_sites": [...]
    }

If you use the `/all` endpoint, all fields will be populated. If you use one of the more specific enpoints, the other fields will be empty. 


## Data

The data for this project is stored in a Google Sheet [here](https://docs.google.com/spreadsheets/d/1AXadba5Si7WbJkfqQ4bN67cbP93oniR-J6uN0_Av958/edit?usp=sharing) (note that there is one worksheet for each data type). If you think that any of the data is wrong, please add a comment directly to the document or write to johannes.rieke@gmail.com. 


## Requirements

TBD


