from geocode import getGeocodeLocation
import json
import httplib2

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

foursquare_client_id = "1KMQEY5XSNAX4JIDJUEXT4LR21WLL3HRFQJ3CKWEU4FE1SYU"
foursquare_client_secret = "MAMSSXHUGF25CAWACUKDIGJZ4ICP00TUEB1YOXIQNNPR14JT"


def findARestaurant(mealType,location):
	#1. Use getGeocodeLocation to get the latitude and longitude coordinates of the location string.
	latitude, longitude = getGeocodeLocation(location)
	#2.  Use foursquare API to find a nearby restaurant with the latitude, longitude, and mealType strings.
	#HINT: format for url will be something like https://api.foursquare.com/v2/venues/search?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&v=20130815&ll=40.7,-74&query=sushi
	url = ( 'https://api.foursquare.com/v2/venues/search?client_id=%s&client_secret=%s&v=20130815&ll=%s,%s&query=%s'\
		    %( foursquare_client_id, foursquare_client_secret, latitude, longitude, mealType ))
	h = httplib2.Http()
	result = json.loads(h.request(url, method="GET")[1])

	if result['response']['venues']:
		venue = result['response']['venues'][0]
		venue_id = venue['id']
		venue_name = venue['name']
		venue_address = ' '.join( venue['location']['formattedAddress'] )

		url = ( 'https://api.foursquare.com/v2/venues/%s/photos?client_id=%s&client_secret=%s&v=20150603' \
				%( venue_id, foursquare_client_id, foursquare_client_secret ))
		
		content = json.loads( h.request(url, method="GET")[1] )

		if content['response']['photos']['items']:
			photo = content['response']['photos']['items'][0]
			prefix = photo['prefix']
			suffix = photo['suffix']
			image_url = prefix + "300*300" + suffix 
		else:
			image_url = "a.jpg"
		
		restaurant = {
			'name': venue_name,
			'address': venue_address,
			'image_url': image_url
		}

		print venue_name, venue_address, image_url

		return restaurant

	else:
		print 'Can not find a suitable restaurant'
		return "No restaurant found"
	#3. Grab the first restaurant
	#4. Get a  300x300 picture of the restaurant using the venue_id (you can change this by altering the 300x300 value in the URL or replacing it with 'orginal' to get the original picture
	#5. Grab the first image
	#6. If no image is available, insert default a image url
	#7. Return a dictionary containing the restaurant name, address, and image url	
if __name__ == '__main__':
	findARestaurant("Pizza", "Tokyo, Japan")
	findARestaurant("Tacos", "Jakarta, Indonesia")
	findARestaurant("Tapas", "Maputo, Mozambique")
	# findARestaurant("Falafel", "Cairo, Egypt")
	# findARestaurant("Spaghetti", "New Delhi, India")
	# findARestaurant("Cappuccino", "Geneva, Switzerland")
	# findARestaurant("Sushi", "Los Angeles, California")
	# findARestaurant("Steak", "La Paz, Bolivia")
	# findARestaurant("Gyros", "Sydney Australia")
