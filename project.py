from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
#new imports for creating anti forgery state token
#login_session acts like a dictionary for the user to store info in
from flask import session as login_session
import random
import string
import datetime
#need to recieve code sent back from the callback method
# IMPORTS FOR THIS STEP
#stores client Id, client secret and other OAuth 2.0 parameters
from oauth2client.client import flow_from_clientsecrets
#if we run into an erryor trying to exchange an authorization code for an access token. This catches the error
from oauth2client.client import FlowExchangeError
import httplib2
#converting in memory python to json (java script object notation)
import json
from flask import make_response
#apache 2 HTTP library
import requests

app = Flask(__name__)

#declraes my client ID
CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

#Connect to Database and create database session
#updated engine to take from db with users
engine = create_engine('sqlite:///itemcatalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#JSON APIs to view Catalog Information
@app.route('/catalog/JSON')
def catalogJSON():
	categories = session.query(Category).all()
	return jsonify(catalog=[r.serialize for r in categories])

@app.route('/catalog/<string:category_name>/JSON')
def itemsJSON(category_name):
	category = session.query(Category).filter_by(name=category_name).first()
	items = session.query(Item).filter_by(category = category).all()
	return jsonify(Items=[i.serialize for i in items])

# Create anti-forgery state token
#store it in the session for later validation
@app.route('/login')
def showLogin():
	#state is a 32 character long and mix of upper case and digits
	#attackers would have to guess this code in order to make a request on the user's behalf
	#later we check if the user and the login session still have the same state value when a user tries to authenticate
	state = ''.join(random.choice(string.ascii_uppercase + string.digits)
					for x in xrange(32))
	login_session['state'] = state
	#return "The current session state is %s" % login_session['state']
	#loads to login button, but still need to let the server know that the user has been successfully authenticated
	return render_template('login.html', STATE=state)

#server side function,  https://classroom.udacity.com/nanodegrees/nd004/parts/0041345408/modules/348776022975461/lessons/3967218625/concepts/41458490190923
# https://github.com/udacity/ud330/blob/master/Lesson2/step6/project.py
@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Validate state token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	# Obtain authorization code
	code = request.data

	try:
		# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(
			json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid.
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
		   % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	# If there was an error in the access token info, abort.
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'),
								 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Store the access token in the session for later use.
	login_session['access_token'] = credentials.access_token
	login_session['gplus_id'] = gplus_id

	# Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']
	# ADD PROVIDER TO LOGIN SESSION
	login_session['provider'] = 'google'

	# see if user exists, if it doesn't make a new one
	user_id = getUserID(data["email"])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("you are now logged in as %s" % login_session['username'])
	print "done!"
	return output

# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            #could have problems with this these two lines below
            #if login_session['credentials']:
              #del login_session['credentials']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))

# User Helper Functions
def createUser(login_session):
	newUser = User(name=login_session['username'], email=login_session[
				   'email'], picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	user = session.query(User).filter_by(id=user_id).one()
	return user

def getUserID(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user.id
	except:
		return None

# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
	# Only disconnect a connected user.
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(
			json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	access_token = credentials.access_token
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	if result['status'] != '200':
		# For whatever reason, the given token was invalid.
		response = make_response(
			json.dumps('Failed to revoke token for given user.'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response

#Show all categories
#renders different html docs depending on user
@app.route('/')
@app.route('/catalog/')
def showCategories():
  categories = session.query(Category).order_by(asc(Category.name))
  items = session.query(Item).order_by(asc(Item.dateAdded))
  return render_template('catalog.html', categories = categories, items = items)

#Show a category's catalog
#renders different html docs depending on user
@app.route('/catalog/<string:category_name>/')
@app.route('/catalog/<string:category_name>/items/')
def showItems(category_name):
	categories = session.query(Category).order_by(asc(Category.name))
	category = session.query(Category).filter_by(name = category_name).one()
	items = session.query(Item).filter_by(category_id = category.id).all()
	numberOfItems = session.query(Item).filter_by(category = category).count()
	return render_template('category.html', items = items, category = category, categories = categories, numberOfItems = numberOfItems)

#shows an item's description
#renders different html docs depending on user
@app.route('/catalog/<string:category_name>/<string:item_name>', methods = ['GET', 'POST'])
def showItem(category_name, item_name):
	categories = session.query(Category).order_by(asc(Category.name))
	category = session.query(Category).filter_by(name = category_name).one()
	item = session.query(Item).filter_by(name = item_name).first()
	return render_template('item.html', category = category, item = item, categoires = categories)

#Create a new item
@app.route('/catalog/new',methods=['GET','POST'])
def newItem():
  if 'username' not in login_session:
	return "<script>function myFunction() {alert('You are not authorized to add items to this catalog. Please login.');}</script><body onload='myFunction()''>"
  if request.method == 'POST':
	user = getUserInfo(login_session['user_id'])
	category = session.query(Category).filter_by(name = request.form['category']).one()
	newItem = Item(name = request.form['name'], description = request.form['description'], price = request.form['price'], dateAdded = datetime.date.today(), category = category, user = user)
	session.add(newItem)
	session.commit()
	flash('New Menu %s Item Successfully Created' % (newItem.name))
	return redirect(url_for('showItems', category_name = category.name))
  else:
	return render_template('newmenuitem.html')

#Edit a menu item
@app.route('/catalog/<string:item_name>/edit', methods=['GET','POST'])
def editItem(item_name):
	if 'username' not in login_session:
		return "<script>function myFunction() {alert('You are not authorized to edit items to this catalog. Please login.');}</script><body onload='myFunction()''>"
	editedItem = session.query(Item).filter_by(name = item_name).first()
	if login_session['user_id'] != editedItem.user_id:
	  return "<script>function myFunction() {alert('You are not authorized to edit menu items to this restaurant. Please create your own restaurant in order to edit items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		if request.form['name']:
			editedItem.name = request.form['name']
		if request.form['description']:
			editedItem.description = request.form['description']
		if request.form['price']:
			editedItem.price = '$' + request.form['price']
		session.add(editedItem)
		session.commit() 
		flash('Item Successfully Edited')
		return redirect(url_for('showItem', category_name = editedItem.category.name, item_name = editedItem.name))
	else:
		return render_template('edititem.html', item = editedItem)

#Delete a menu item
@app.route('/catalog/<string:item_name>/delete', methods = ['GET','POST'])
def deleteItem(item_name):
	if 'username' not in login_session:
	  return "<script>function myFunction() {alert('You are not authorized to delete items to this restaurant. Please create your own restaurant in order to delete items.');}</script><body onload='myFunction()''>"
	itemToDelete = session.query(Item).filter_by(name = item_name).first()
	category = itemToDelete.category
	if login_session['user_id'] != itemToDelete.user_id:
	  return "<script>function myFunction() {alert('You are not authorized to delete items to this restaurant. Please create your own restaurant in order to delete items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		session.delete(itemToDelete)
		session.commit()
		flash('Menu Item Successfully Deleted')
		return redirect(url_for('showItems', category_name = category.name))
	else:
		return render_template('deleteMenuItem.html', item = itemToDelete)



if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)