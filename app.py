from flask import Flask, jsonify, Response
import requests
import json

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Ok!", 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def error_404(path):
    return jsonify({'error': 'Not Found', 'path': path}), 404

@app.route('/realty-listing/<int:p_page_number>/<int:p_page_size>/<string:p_portal_type>/<int:p_is_venda>', methods=['GET'])
def get_realty_list(p_page_number, p_page_size, p_portal_type, p_is_venda):
    data = get_realty_from_database()
    p_business_type = get_business_type(p_is_venda)
    minItem, maxItem = get_max_min_page(p_page_number, p_page_size)
    
    json_object = get_filtered_realty_list(p_portal_type, data, p_business_type)

    output_dict_count = [x for x in json_object if x['index'] > -1]

    output_dict = [x for x in json_object if x['index'] >= minItem and x['index'] <= maxItem]

    output_json = json.dumps(output_dict)

    return Response("{ \"pageNumber\": " + str(p_page_number) + ", \"pageSize\": " + str(p_page_size) + ", \"totalCount\": " + str(len(output_dict_count)) + ", \"listing\": " + output_json + "}", mimetype='application/json')



def get_realty_from_database():
    req = requests.get('http://grupozap-code-challenge.s3-website-us-east-1.amazonaws.com/sources/source-2.json')
    return req.content

def get_business_type(p_is_venda):
    if p_is_venda <= 0:
        return 'RENTAL'
    if p_is_venda > 0:
        return 'SALE'

def get_max_min_page(p_page_number, p_page_size):
    page_number = p_page_number
    page_size = p_page_size
    
    page_size_calc = page_size-1
    maxItem = page_size_calc*page_number
    minItem = maxItem-page_size_calc

    if page_number > 1:
        minItem += page_number-1
        maxItem += page_number-1
    
    if page_size <= 0:
        page_size = 1
    if page_number <= 0:
        page_number = 1
    
    if page_number == 1 and page_size == 1:
        minItem = 0
        maxItem = 0

    return minItem, maxItem

def get_filtered_realty_list(p_portal_type, p_data, p_business_type):
    json_object = json.loads(p_data)

    count = 0
    for item in json_object:
        item['index'] = -1

        viva_max_rental_price = 4000
        viva_max_sale_price = 700000
        zap_min_rental_price = 3500
        zap_min_sale_price = 600000

        latitude = item['address']['geoLocation']['location']['lat']
        longitude = item['address']['geoLocation']['location']['lon']
        
        usable_areas = item['usableAreas']
        business_type = ""
        sale_price = 0
        rental_price = 0
        monthly_condo_fee = None
        
        if 'businessType' in item['pricingInfos']:
            business_type = item['pricingInfos']['businessType']
        if 'price' in item['pricingInfos']:
            sale_price = float(item['pricingInfos']['price'])
        if 'rentalTotalPrice' in item['pricingInfos']:
            rental_price = float(item['pricingInfos']['rentalTotalPrice'])
        if 'monthlyCondoFee' in item['pricingInfos']:
            monthly_condo_fee = float(item['pricingInfos']['monthlyCondoFee'])

        if monthly_condo_fee is None:
            monthly_condo_fee = 0

        if latitude != 0 and longitude != 0:
            is_bounding_box_grupo_zap = False
            if latitude >= -23.568704 and latitude <= -23.546686:
                if longitude >= -46.693419 and longitude <= -46.641146:
                    viva_max_rental_price = 6000
                    viva_max_sale_price = 1050000

                    zap_min_rental_price = 3150
                    zap_min_sale_price = 540000

            if (business_type == p_business_type):
                if p_portal_type.upper() == 'ZAP':
                    if 'SALE' in business_type and sale_price > zap_min_sale_price:
                        if ((('SALE' in business_type and usable_areas > 3500) or ('SALE' in business_type and usable_areas <= 0))):
                            item['index'] = count
                            count = count + 1
                    elif 'RENTAL' in business_type and rental_price > zap_min_rental_price:
                        item['index'] = count
                        count = count + 1

                elif p_portal_type.upper() == 'VIVAREAL':
                    if 'SALE' in business_type and sale_price <= viva_max_sale_price:
                        item['index'] = count
                        count = count + 1
                    elif (('RENTAL' in business_type and rental_price <= viva_max_rental_price)):
                        if ('monthlyCondoFee' in item['pricingInfos']):
                            thirty_percentage_value = float(rental_price) * 30 / 100
                            if monthly_condo_fee < thirty_percentage_value:
                                item['index'] = count
                                count = count + 1
                        else:
                            item['index'] = count
                            count = count + 1

    return json_object

if __name__ == '__main__':
    app.run(debug=True)