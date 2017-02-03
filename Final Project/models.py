from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import random, string
import datetime
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

Base = declarative_base()
secret_key = ''.join(random.choice(string.letters + string.digits) for idx in range(32))

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    username = Column(String(32), index = True)
    password_hash = Column(String(64))
    email = Column(String, index = True)
    picture = Column(String)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)
    
    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration = 600):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(secret_key)

        try:
            data = s.loads(token)
        except SignatureExpired:
            print 'token expired.'
            return None
        except BadSignature:
            print 'invaild token'
            return None

        user_id = data['id']
        return user_id

    @staticmethod
    def validate(item):
        required_fields = ['username', 'password', 'email']
        errors = []

        if type(item)!=dict:
            errors.append({'error': "item must be a dict"})
        else:
            for key in required_fields:
                if not key in item:
                    error = {key : 'required'}
                    errors.append(error)
                elif not item[key]:
                    error = {key : 'required'}
                    errors.append(error)

        return errors

    @property
    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'picture': self.picture,
        }

class Request(Base):
    """ docstring """
    __tablename__ = 'request'
    id = Column(Integer, primary_key = True)
    meal_type = Column(String(128))
    location_string = Column(String(128))
    latitude = Column(Float)
    longitude = Column(Float)
    meal_time = Column(String(64))
    filled = Column(Boolean, default = False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @staticmethod
    def validate(item):
        errors = []
        required_fields = ['meal_type', 'location_string', 'longitude', 'latitude', 'meal_time']
        if type(item) == dict:
            for key in required_fields:
                if not key in item:
                    errors.append({ key : 'required' })
                elif not item[key]:
                    errors.append({ key : 'required' })
        else:
            errors.append({ "error": 'item must be a dict' })

        return errors

    @property
    def serialize(self):
        return {
            'id': self.id,
            'meal_type': self.meal_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'meal_time': self.meal_time,
            'location_string': self.location_string,
            'filled': self.filled
        }

class Proposal(Base):
    __tablename__ = 'proposal'
    id = Column(Integer, primary_key = True)
    user_proposed_to = Column(Integer)
    user_proposed_from = Column(Integer)
    request_id = Column(Integer, ForeignKey('request.id'))
    filled = Column(Boolean, default = False)
    request = relationship(Request)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'user_proposed_to': self.user_proposed_to,
            'user_proposed_from': self.user_proposed_from,
            'filled': self.filled
        }
    
    @staticmethod
    def validate(item):
        required_fields = ['request_id']
        errors = []

        if type(item) == dict:
            for key in required_fields:
                if not key in required_fields:
                    errors.append({ key : 'required' })
                elif not item[key]:
                    errors.append({ key : 'required' })
        else:
            errors.append({"error": 'item must be a dict'})

        return errors

class MealDate(Base):
    __tablename__ = "mealdate"
    id = Column(Integer, primary_key = True)
    user_1 = Column(Integer)
    user_2 = Column(Integer)
    restaurant_name =  Column(String(128))
    restaurant_address = Column(String(128))
    restaurant_picture = Column(String(256))
    meal_time = Column(String)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'user_1': self.user_1,
            'user_2': self.user_2,
            'restaurant_name': self.restaurant_name,
            'restaurant_address': self.restaurant_address,
            'restaurant_picture': self.restaurant_picture,
            'meal_time': self.meal_time
        }

    @staticmethod
    def validate(data):
        required_fields = ['accept_proposal', 'proposal_id']
        errors = []
        if type(data) != dict:
            error = dict({"Missing required parameters":" ".format(', '.join(required_fields))})
            errors.append(error)
        else:
            for key in required_fields:
                if not key in data:
                    errors.append({ value: "Required" })
                else:
                    if not data[value]:
                        errors.append({ value: "Required" })
        return errors


engine = create_engine('sqlite:///meatneat.db')

Base.metadata.create_all(engine)