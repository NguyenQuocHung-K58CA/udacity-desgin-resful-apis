from flask import Flask, request, jsonify
from flask import session, g
from flask import abort, flash, make_response, render_template
from models import Base, User, Request, Proposal, MealDate
from flask_httpauth import HTTPBasicAuth

from findARestaurant import findARestaurant
import random, string

from datetime import datetime, time

from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

auth = HTTPBasicAuth()

engine = create_engine('sqlite:///meatneat.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind = engine)
session = DBSession()

app = Flask(__name__)

@auth.verify_password
def verify_password(username_or_token, password):
    user_id = User.verify_auth_token(username_or_token)

    if not user_id is None:
        user = session.query(User).filter_by(id = user_id).one()
    else:
        user = session.query(User).filter_by(username = username_or_token).first()
        if not user or not user.verify_password(password):
            print 'Invaild username or password'
            return False

    g.user = user
    return True


@app.route('/api/v1/<provider>/login', methods = ['POST'])
def login(provider):
    #STEP 1 - Parse the auth code
    auth_code = request.json.get('auth_code')
    print "Step 1 - Complete, received auth code %s" % auth_code
    if provider == 'google':
        #STEP 2 - Exchange for a token
        try:
            # Upgrade the authorization code into a credentials object
            oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(auth_code)
        except FlowExchangeError:
            response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Check that the access token is valid.
        access_token = credentials.access_token
        url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])
        # If there was an error in the access token info, abort.
        if result.get('error') is not None:
            response = make_response(json.dumps(result.get('error')), 500)
            response.headers['Content-Type'] = 'application/json'
        print "Step 2 Complete! Access Token : %s " % credentials.access_token

        #STEP 3 - Find User or make a new one
        
        #Get user info
        h = httplib2.Http()
        userinfo_url =  "https://www.googleapis.com/oauth2/v1/userinfo"
        params = {'access_token': credentials.access_token, 'alt':'json'}
        answer = requests.get(userinfo_url, params=params)
      
        data = answer.json()

        name = data['name']
        picture = data['picture']
        email = data['email']

        #see if user exists, if it doesn't make a new one
        user = session.query(User).filter_by(email=email).first()
        if not user:
            user = User(username = name, picture = picture, email = email)
            session.add(user)
            session.commit()

        #STEP 4 - Make token
        token = user.generate_auth_token(600)

        #STEP 5 - Send back token to the client 
        return jsonify({'token': token.decode('ascii')})
        #return jsonify({'token': token.decode('ascii'), 'duration': 600})
    else:
        return 'Unrecoginized Provider'

@app.route('/api/v1/<provider>/logout', methods = ['POST'])
@auth.login_required
def logout(provider):
    g.user = None
    return jsonify({'response': True})

@app.route('/token', methods = ['GET'])
@auth.login_required
def get_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')}), 200

@app.route('/api/v1/users', methods = ['GET'])
@auth.login_required
def get_users():
    users = session.query(User).all()
    users = [user.serialize for user in users]
    return jsonify({'users': users})

@app.route('/api/v1/users/<int:id>', methods = ['GET'])
@auth.login_required
def get_user_profile(user_id):
    user = session.query(User).filter_by(id = id).one()
    if not user:
        abort(400)
    return jsonify({'user': user.serialize})

@app.route('/api/v1/users', methods = ['POST'])
def create_newuser():
    username = request.json.get('username')
    password = request.json.get('password')
    
    if username is None or password is None:
        print 'Missing paramaters'
        return jsonify({'error': 'Username and password required'})

    user = session.query(User).filter_by(username = username).first()
    if user is not None:
        print 'username exist'
        return jsonify({'user': user.serialize})
    user = User(username = username)
    user.hash_password(password)

    session.add(user)
    session.commit()
    return jsonify({'user': user.serialize})

@app.route('/api/v1/users', methods = ['PUT'])
@auth.login_required
def update_user():
    data = request.json
    return jsonify({'data': data})


@app.route('/api/v1/requests', methods = ['GET'])
@auth.login_required
def get_all_requests():
    user = g.user
    requests = session.query(Request).filter(user.id != Request.user_id).all()
    requests = [req.serialize for req in requests]
    return jsonify({'requests' : requests})

@app.route('/api/v1/requests', methods = ['POST'])
@auth.login_required
def create_newrequest():
    errors = Request.validate(request.json)
    if len(errors)==0:
        user = g.user
        meal_type = request.json.get('meal_type')
        location_string = request.json.get('location_string')
        latitude = request.json.get('latitude')
        longitude = request.json.get('longitude')
        meal_time = request.json.get('meal_time')

        req = Request(meal_type = meal_type, meal_time = meal_time, \
                      location_string = location_string, user_id = user.id, \
                      latitude = latitude, longitude = longitude)
        session.add(req)
        session.commit()
        return jsonify({'result': True}), 201
    else:
        return jsonify({'errors': errors}), 400

@app.route('/api/v1/requests/<int:id>', methods = ['GET'])
@auth.login_required
def get_request_by_id(id):
    req = session.query(Request).filter_by(id = id).one()
    if not req:
        abort(400)
    else:
        return jsonify({'request': req})

@app.route('/api/v1/requests/<int:id>', methods = ['PUT'])
@auth.login_required
def update_request(id):
    user = g.user
    req = session.query(Request).filter(and_(Request.id == id, user.id != Request.user_id))
    if not req:
        abort(400)

    errors = Request.validate(request.json)
    if len(errors)==0:
        meal_type = request.json.get('meal_type')
        location_string = request.json.get('location_string')
        latitude = request.json.get('latitude')
        longitude = request.json.get('longitude')
        meal_time = request.json.get('meal_time')
        new_req = {
            'meal_type': meal_type,
            'meal_time': meal_time,
            'latitude' : latitude,
            'longitude': longitude,
            'location_string': location_string
        }
        req.update(new_req)
        session.commit()
        return jsonify({'response': True})
    else:
        return jsonify({'errors': errors}), 400

@app.route('/api/v1/requests/<int:id>', methods = ['DELETE'])
@auth.login_required
def delete_request(id):
    user = g.user
    req = session.query(Request).filter(and_(Request.id == id, user.id != Request.id)).first()

    if not req:
        abort(400)

    session.delete(req)
    session.commit()
    return jsonify({'response': True})



@app.route('/api/v1/proposals', methods = ['GET'])
@auth.login_required
def get_all_proposals():
    user = g.user
    proposals = session.query(Proposal).filter_by(user_proposed_to = user.id).all()
    proposals = [proposal.serialize for proposal in proposals]
    return jsonify({'proposals': proposals}), 200

@app.route('/api/v1/proposals', methods = ['POST'])
@auth.login_required
def create_newproposal():
    errors = Proposal.validate(request.json)

    if len(errors)==0:
        user_proposed_from = g.user.id
        request_id = request.json.get('request_id')

        req = session.query(Request).filter_by(id = request_id).first()
        if req is None:
            return jsonify({'errors': 'Request is not exist'})
        else:
            user_proposed_to = req.user_id
            proposal = Proposal(request_id = request_id, \
                                user_proposed_from = user_proposed_from, user_proposed_to=user_proposed_to )
            session.add(proposal)
            session.commit()
            return jsonify({'response': True}), 201
    else:
        return jsonify({'errors': errors})

@app.route('/api/v1/proposals/<int:id>', methods = ['GET'])
@auth.login_required
def get_proposal_by_id(id):
    user = g.user
    proposals = session.query(Proposal).filter(or_( \
                             Proposal.user_proposed_from == user.id, \
                             Proposal.user_proposed_to == user.id   \
                            )).all()
    proposals = [proposal.serialize for proposal in proposals]
    return jsonify({'proposals': proposals})
    

@app.route('/api/v1/proposals/<int:id>', methods = ['PUT'])
@auth.login_required
def update_proposal(id):
    errors = Proposal.validate(request.json)
    if len(errors)>0:
        return jsonify({'errors': errors}), 400

    user = g.user
    proposal = session.query(Proposal).filter(and_( \
        Proposal.id == id, \
        Proposal.user_proposed_from == user.id \
    ))
    if not proposal:
        abort(400)

    user_proposed_from = user.id
    request_id = request.json.get('request_id')

    req = session.query(Request).filter_by(id = request_id).first()
    if req is None:
        return jsonify({'errors': 'Request is not exist'})
    else:
        user_proposed_to = req.user_id
        proposal = {
                    'request_id' : request_id, 
                    'user_proposed_from' : user_proposed_from, 
                    'user_proposed_to' : user_proposed_to 
            }
        proposal.update(proposal)
        session.commit()
        return jsonify({'response': True}), 201

@app.route('/api/v1/proposals/<int:id>', methods = ['DELETE'])
@auth.login_required
def delete_proposal(id):
    user = g.user
    proposal = session.query(Proposal).filter(and_( \
        Proposal.id == id, \
        user.id == Proposal.user_proposed_from \
    )).first()

    if proposal is None:
        abort(400)
    
    session.delete(proposal)
    session.commit()
    return jsonify({'response': True})

@app.route('/api/v1/dates', methods = ['GET'])
@auth.login_required
def get_all_dates():
    user = g.user
    dates = session.query(MealDate).filter(or_( \
        MealDate.user_1 == user.id,  \
        MealDate.user_2 == user.id  \
    ))
    dates = [date.serialize for date in dates]

    return jsonify({'dates': dates}), 200

@app.route('/api/v1/dates', methods = ['POST'])
@auth.login_required
def create_newdate():
    errors = MealDate.validate(request.json)
    if len(errors) == 0:
        proposal_id = request.json.get('proposal_id')
        accept_proposal = request.json.get('accept_proposal')

        proposal = session.query(Proposal).filter_by(id = proposal_id).first()
        if proposal is None:
            return jsonify({'response': False})
        
        req = proposal.request
        if req.filled:
            return jsonify({'response': False})
        if accept_proposal:
            proposal.update({'filled': True})
            req.update({'filled': True})

            restaurant_name = ''
            restaurant_address = ''
            restaurant_picture = ''

            try:
                restaurant = findARestaurant(req.meal_type, req.location_string)
                if type(restaurant) == dict:
                    restaurant_name = restaurant['name']
                    restaurant_address = restaurant['address']
                    restaurant_picture = restaurant['image_url']
            except Exception as e:
                print e

            date = MealDate(
                user_1 = req.user_id,   \
                user_2 = proposal.user_proposed_from,   \
                restaurant_name =  restaurant_name,     \
                restaurant_address = restaurant_address,    \
                restaurant_picture = restaurant_picture,    \
                meal_time = req.meal_time   \
            )
            session.add(date)
            session.commit()
            return jsonify({'response': True}), 201
        else:
            session.delete(proposal)
            session.commit()
            return jsonify({'response': 'Deleted proposal'})
    else:
        return jsonify({'errors': errors}), 400


@app.route('/api/v1/dates/<int:id>', methods = ['GET'])
@auth.login_required
def get_date_by_id(id):
    user = g.user
    meal_date = session.query(MealDate).filter(and_(    \
        MealDate.id == id,  \
        or_(user.id == MealDate.user_1, user.id == MealDate.user_2) \
    )).first()

    if meal_date is None:
        abort(404)
    return jsonify({'meal_date': meal_date}), 200
    

@app.route('/api/v1/dates/<int:id>', methods = ['PUT'])
@auth.login_required
def update_date(id):
    return jsonify({'response': True})

@app.route('/api/v1/dates/<int:id>', methods = ['DELETE'])
@auth.login_required
def delete_date(id):
    user = g.user
    meal_date = session.query(MealDate).filter(and_(    \
        MealDate.id == id,  \
        or_(user.id == MealDate.user_1, user.id == MealDate.user_2) \
    )).first()

    if meal_date is None:
        abort(400)
    
    session.delete(meal_date)
    session.commit()

    return jsonify({'response': True})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)


