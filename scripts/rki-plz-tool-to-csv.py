import xml.etree.ElementTree
import csv

# This script takes data about health departments from the RKI PLZ Tool 
# and converts it from xml to csv.
# Download the xml file from here: https://www.rki.de/DE/Content/Infekt/IfSG/Software/Aktueller_Datenbestand.html

# Open xml file
filename = 'TransmittingSiteSearchText 2.xml'
root = xml.etree.ElementTree.parse(filename).getroot()

# Open csv file and set up writer
with open('rki_data.csv', 'w') as csvfile:
    writer = csv.writer(csvfile, delimiter=',')

    # Iterate over all health departments in xml
    for dep in root:

        # Concatenate all search terms in the children
        search_terms = [search_term.attrib.get(
            'Value', '') for search_term in dep]
        search_terms_str = str.join(', ', search_terms)

        # Write all values to csv
        writer.writerow(
            [dep.attrib['Name'], dep.attrib['Code'], dep.attrib['Department'], dep.attrib['Street'], dep.attrib['Postalcode'], dep.attrib['Place'], dep.attrib['Phone'], dep.attrib['Fax'], dep.attrib['Email'], search_terms_str])

