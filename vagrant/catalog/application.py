#
# Item Catalog webserver
# By: Jason van Biezen
# 

import sys
sys.path.insert(0, 'libs')
import os

from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask import flash
from werkzeug import secure_filename
from flask import send_from_directory

from functools import wraps
app = Flask(__name__)
UPLOAD_FOLDER = 'user_data/uploads/'
ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

from sqlalchemy import create_engine, asc, or_, and_
from sqlalchemy.orm import sessionmaker

from bfs_core_database import Base, User, Image, Catalog, Catagory, Item

#######
#
# Oauth Login Imports
#

from flask import session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2, json
from flask import make_response
import requests

#
#######

#Connect to Database and create database db
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
db = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

#######
#
# Oauth User Account
#

def createUser(session):
    newUser = User(name = session['username'],
                   email = session['email'],
                   picture = session['picture'])
    db.add(newUser)
    db.commit()
    user = db.query(User).filter(User.email == session['email']).first()
    return user.id

def getUserInfo(user_id):
    user = db.query(User).filter(User.id == user_id).first()
    return user

def getUserID(email):
    try:
        user = db.query(User).filter(User.email == email).first()
        return user.id
    except:
        return None

def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

#
#######


#######
#
# Image Uploading
#

def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/images/<int:image_id>')
def uploaded_image(image_id):
    image = db.query(Image).filter_by(id=image_id).get()
    if image:
        return send_from_directory(app.config['UPLOAD_FOLDER'], image.filename)

def save_image(file):
    if file and allowed_image_file(file.filename):
        filename = secure_filename(file.filename)
        ext = os.path.splitext(file.filename)[1]
        exists = os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],
                                             filename)
                               )
        while exists:
            filename = ''.join(random.choice(
                                  string.ascii_lowercase +
                                  string.ascii_uppercase +
                                  string.digits) for i in range(12)) + ext
            exists = os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],
                                                 filename)
                                   )
        filename = secure_filename(filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_image = Image(filename=filename)
        db.add(new_image)
        db.commit()
        image = db.query(Image).filter_by(filename=filename).first()
        return image
    return None

def remove_file(filename):
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
def remove_catalog(catalog_id):
    """ 
    Removes catalog, and all related catagories and items.

    Keyword arguments:
    catalog_id -- The row ID of the catalog to be deleted.

    Returns: name of deleted catalog, or None if delete failed.
    """
    catalog = db.query(Catalog).filter_by(id = catalog_id).first()
    if catalog:
        # First remove catalog catagories, if they exist:
        catagories = db.query(Catagory)\
                       .filter_by(catalog_id=catalog.id)\
                       .all()
        for catagory in catagories:
            remove_catagory(catagory.id)
        name = catalog.name
        header_image = catalog.header_image
        db.query(Catalog).filter_by(id = catalog_id).delete()
        db.query(Image).filter_by(filename=header_image).delete()
        db.commit()
        if header_image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],header_image))
        return name
    return None

def remove_catagory(catagory_id):
    """ 
    Removes catagory, and all catagory items.

    Keyword arguments:
    catagory_id -- The row ID of the catagory to be deleted.
    
    Returns: name of deleted catagory, or None if delete failed.
    """
    catagory = db.query(Catagory).filter_by(id=catagory_id).first()
    if catagory:
        # First remove all items associated with this catagory
        items = db.query(Item).filter_by(catagory_id=catagory_id).all()
        for item in items:
            remove_item(item.id)
        name = catagory.name
        catagory_image = catagory.catagory_image
        db.query(Catagory).filter_by(id=catagory_id).delete()
        db.query(Image).filter_by(filename=catagory_image).delete()
        db.commit()
        if catagory_image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],catagory_image))
        return name
    return None

def remove_item(item_id):
    """ 
    Removes item indicated by its row ID.

    Keyword arguments:
    item_id -- The row ID of the item to be deleted.

    Returns: name of deleted item, or None if delete failed.
    """
    item = db.query(Item).filter_by(id=item_id).first()
    if item:
        name = item.name
        item_image = item.item_image
        db.query(Item).filter_by(id=item_id).delete()
        db.query(Image).filter_by(filename=item_image).delete()
        db.commit()
        if item_image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],item_image))
        return name
    return None

#
#######

#######
#
# Oauth Login
#

@app.route('/login/')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state', '') != session['state']:
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
    if result.get('danger') is not None:
        response = make_response(json.dumps(result.get('danger')), 500)
        response.headers['Content-Type'] = 'application/json'

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
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = session.get('credentials')
    stored_gplus_id = session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id: 
        # Fix limbo sign-in bug by re-saving user detail
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        params = {'access_token': access_token, 'alt': 'json'}
        answer = requests.get(userinfo_url, params=params)
        data = answer.json()
        session['provider'] = 'google'
        session['access_token'] = access_token
        session['username'] = data['name']
        session['picture'] = data['picture']
        session['email'] = data['email']

        user_id = getUserID(data['email'])
        if not user_id:
            user_id = createUser(session)        
        session['user_id'] = user_id

        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        flash('You are already logged in with Google+, ' + session['username'], 'info')
        return response

    # Store the access token in the db for later use.
    session['access_token'] = access_token
    session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    session['provider'] = 'google'
    session['access_token'] = access_token
    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']

    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(session)
    session['user_id'] = user_id

    output = '<div style="width:500px;margin:0 auto;">'
    output += '<h1>Welcome, '
    output += session['username']
    output += '!</h1>'
    output += '<img src="'
    output += session['picture']
    output += ' " style = "margin:0 auto;width: 300px;height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    output += "</div>"
    flash("You are now logged in with Google+ as %s" % session['username'], 'success')
    return output

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    session['provider'] = 'facebook'
    session['username'] = data["name"]
    session['email'] = data["email"]
    session['facebook_id'] = data["id"]

    # The token must be stored in the session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(session['email'])
    if not user_id:
        user_id = createUser(session)
    session['user_id'] = user_id

    output = '<div style="width:500px;margin:0 auto;">'
    output += '<h1>Welcome, '
    output += session['username']

    output += '!</h1>'
    output += '<img src="'
    output += session['picture']
    output += ' " style = "margin:0 auto;width: 300px; height: 300px;"> '
    output += '</div>'

    flash("You are now logged in with facebook as %s" % session['username'], 'success')
    return output

@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = session['facebook_id']
    # The access token must me included to successfully logout
    access_token = session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

@app.route('/gdisconnect')
def gdisconnect():
    if session.get('access_token') is None:
        if session.get['username'] is None:
            response = make_response(json.dumps('User not logged in.'), 400)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            response = make_response(json.dumps(
                "User %s's access token not found.  Please login," \
                "then try logging out again."), 400)
            response.headers['Content-Type'] = 'application/json'
            return response
    access_token = session['access_token'] if 'access_token' in session else None
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    return "you have been logged out"

@app.route('/disconnect')
def disconnect():
    if 'provider' in session:
        if session['provider'] == 'google':
            gdisconnect()
            del session['gplus_id']
            del session['access_token']
        if session['provider'] == 'facebook':
            fbdisconnect()
            del session['facebook_id']
        del session['username']
        del session['email']
        del session['picture']
        del session['user_id']
        del session['provider']
        flash("You have successfully been logged out.", 'success')
        return redirect(url_for('show_catalogs'))
    else:
        flash("You were not logged in", 'info')
        if 'username' in session:
            del session['username']
        if 'email' in session:
            del session['email']
        if 'picture' in session:
            del session['picture']
        if 'user_id' in session:
            del session['user_id']
        if 'provider' in session:
            del session['provider']
        if 'access_token' in session:
            del session['access_token']
        if 'gplus_id' in session:
            del session['gplus_id']
        if 'facebook_id' in session:
            del session['facebook_id']
        return redirect(url_for('show_catalogs')) 

#
#######

@app.route('/')
@app.route('/catalogs/')
def show_catalogs():
    if 'user_id' in session:
        catalogs = db.query(Catalog) \
                     .filter(or_(Catalog.public == True,
                                 Catalog.user_id == session['user_id']
                                )
                            ) \
                     .all()
    else:
        catalogs = db.query(Catalog).filter_by(public = True).all()

    return render_template('catalogs.html', catalogs=catalogs)

@app.route('/catalogs/user/')
@requires_login
def user_catalogs():
    catalogs = db.query(Catalog).filter_by(user_id=session['user_id']).all()
    return render_template('catalogs.html', catalogs=catalogs)

@app.route('/catalogs/create/', methods=['GET','POST'])
@requires_login
def create_catalog():
    if request.method == 'GET':
        return render_template('create_catalog.html')
    elif request.method == 'POST':
       name = request.form.get('name')
       public = True if request.form.get('public') else False 
       if not name or len(name) < 3:
           flash("Invalid name!", 'danger')
           return render_template('create_catalog.html',
                                  name=name,
                                  public=public)
       existing_catalog = db.query(Catalog).filter_by(name=name).first()
       if existing_catalog:
           flash("A catalog with that name already exists!", 'danger')
           return render_template('create_catalog.html',
                                  name=name,
                                  public=public)

       file = request.files['header_image']
       if file and allowed_image_file(file.filename):
           image = save_image(file)
       else:
           image = None
       new_catalog = Catalog(name=name,
                            public=public,
                            user_id=session['user_id'],
                            header_image = image.filename if image else None)
       db.add(new_catalog)
       db.commit()
       new_catalog = db.query(Catalog).filter_by(name=name).first()
       flash("New catalog '" + name + "' added!", 'success')
       return redirect(url_for('show_catagories', catalog_id=new_catalog.id))

@app.route('/catalog/<int:catalog_id>/', methods=['GET'])
@app.route('/catalog/<int:catalog_id>/catagories', methods=['GET'])
def show_catagories(catalog_id):
    catalog = db.query(Catalog).filter_by(id = catalog_id).first()
    if not catalog:
        flash("That catalog does not exist!", 'warning')
        return redirect(url_for('show_catalogs'))
    catagories = db.query(Catagory).filter_by(catalog_id = catalog_id).all()
    return render_template('catagories.html', 
                           catalog=catalog,
                           catagories=catagories)

@app.route('/catalog/<int:catalog_id>/delete', methods=['GET','POST'])
@requires_login
def delete_catalog(catalog_id):
    if request.method == 'GET':
        catalog = db.query(Catalog).filter_by(id = catalog_id).first()
        if not catalog:
            flash("Cannot delete catalog: does not exist", 'danger')
            return redirect(url_for('catalogs'))
        else:
            return render_template('delete_catalog.html',
                                   catalog=catalog)
    elif request.method == 'POST':
        name = remove_catalog(catalog_id)
        if name:
            flash("Catalog " + name + " deleted.", 'success')
            return redirect(url_for('show_catalogs'))
        else:
            flash("Error: could not delete catalog.", 'danger')
            return redirect(url_for('show_catalogs'))


@app.route('/catalog/<int:catalog_id>/catagories/create/',
           methods=['GET', 'POST'])
@requires_login
def create_catagory(catalog_id):
    if request.method == 'GET':
        catalog = db.query(Catalog).filter_by(id = catalog_id).first()
        if catalog and session['user_id'] == catalog.user_id:
            catagories = db.query(Catalog)\
                           .filter_by(id=catalog_id).all()
            return render_template('create_catagory.html',
                                   catalog=catalog,
                                   catagories=catagories)
        else:
            if catalog:
                flash('You must be the owner of a catalog to'+
                      ' create new catagories.',
                      'danger')
                return redirect(url_for('show_catagories',
                                        catalog_id=catalog_id))
            else:
                flash('The indicated catagory does not exist.', 'danger')
                return redirect(url_for('show_catalogs'))
    elif request.method == 'POST':
        catalog = db.query(Catalog).filter_by(id = catalog_id).first()
        if catalog and session['user_id'] == catalog.user_id:
            name = request.form.get('name')
            description = request.form.get('description')
            if name:
                catalog = db.query(Catalog)\
                            .filter_by(id = catalog_id)\
                            .first()
                existing_catagory = db.query(Catagory)\
                                      .filter(
                                        and_(Catagory.name==name,
                                             Catagory.catalog_id==catalog_id))\
                                      .first()
                if existing_catagory:
                    flash('Catagory cannot have the same name as an existing'+
                          ' catagory.', 'danger')
                    return redirect(url_for('create_catagory',
                                            catalog_id=catalog_id,
                                            name=name,
                                            description=description)
                                   )
                file = request.files['image']
                if file and allowed_image_file(file.filename):
                    image = save_image(file)
                else:
                    image = None
                new_catagory = Catagory(name=name,
                                        description=description,
                                        catalog_id=catalog_id,
                                        catagory_image=image.filename \
                                                       if image else None)
                db.add(new_catagory)
                db.commit()
                flash('New catagory ' + name + 
                      ' created in catalog ' + catalog.name, 'success')
                return redirect(url_for('show_catagories',
                                        catalog_id=catalog_id))
            else:
                flash('A valid name is required.', 'danger')
                return redirect(url_for('create_catagory',
                                        catalog_id=catalog_id,
                                        name=name,
                                        description=description)) 
        else:
            flash('Catalog not found.  Cannot create new catagory.',
                  'danger')
            return redirect(url_for('show_catalogs'))

@app.route('/catagory/<int:catagory_id>/')
@app.route('/catagory/<int:catagory_id>/items/')
def show_items(catagory_id):
    catagory = db.query(Catagory).filter_by(id=catagory_id).first()
    if catagory:
        catalog = db.query(Catalog).filter_by(id=catagory.catalog_id).first()
        return render_template("items.html",
                               catalog=catalog,
                               catagory=catagory)
    else:
        flash('That catagory does not exist.', 'danger')
        return redirect(url_for('show_catagories',catalog_id=catalog_id))

@app.route('/catagory/<int:catagory_id>/item/create/', methods=['GET','POST'])
@requires_login
def create_item(catagory_id):
    catagory = db.query(Catagory).filter_by(id=catagory_id).first()
    if not catagory:
        flash("Cannot create item in catagory that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    catalog = db.query(Catalog).filter_by(id=catagory.catalog_id).first()
    if not catalog:
        flash("Cannot create item in catalog that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    if session['user_id'] != catalog.user_id:
        flash("You must be the owner of a catalog to create items",
              'danger')
        return redirect(url_for('show_catagories', catalog_id=catalog.id))
    if request.method == 'GET':
        return render_template('create_item.html',
                               catalog = catalog,
                               catagory = catagory)
    elif request.method == 'POST':
        item_name = request.form.get('item_name')
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        row = request.form.get('row')
        rbin = request.form.get('bin')
        existing_item = db.query(Item).filter_by(name = item_name,
                                                 catagory_id = catagory.id)\
                                      .first()
        if existing_item:
            flash("An item with name '%s' already exists in the %s catagory"%\
                  (item_name, catagory.name), 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   catagory = catagory,
                                   item_name = item_name,
                                   description = description,
                                   price = price,
                                   quantity = quantity,
                                   row = row,
                                   bin = rbin)
        try:
            # Casted to float separately so that the invalid text value is
            # repopulated in the form on error.
            price = float(price)
        except ValueError:
            flash('Invalid price', 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   catagory = catagory,
                                   item_name = item_name,
                                   description = description,
                                   price = price,
                                   quantity = quantity,
                                   row = row,
                                   bin = rbin)
        try:
            row = int(row)
            rbin = int(rbin)
        except ValueError:
            flash('Row or Bin is not a valid integer number', 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   catagory = catagory,
                                   item_name = item_name,
                                   description = description,
                                   price = price,
                                   quantity = quantity,
                                   row = row,
                                   bin = rbin)
        file = request.files['image']
        if file and allowed_image_file(file.filename):
            image = save_image(file)
        else:
            image = None
        new_item = Item(name = item_name,
                        description = description,
                        price = price,
                        quantity = quantity,
                        row = row,
                        bin = rbin,
                        catagory_id = catagory.id,
                        item_image = image.filename if image else None)
        db.add(new_item)
        db.commit()
        flash('New item %s added to catagory %s' % \
              (item_name, catagory.name), 'success')
        return redirect(url_for('show_items', catagory_id = catagory.id))
        
@app.route('/catagory/<int:catagory_id>/delete/', methods=['GET','POST'])
@requires_login
def delete_catagory(catagory_id):
    catagory = db.query(Catagory).filter_by(id=catagory_id).first()
    if catagory:
        catalog_id = catagory.catalog_id
        catalog = db.query(Catalog).filter_by(id=catalog_id).first()
        if session['user_id'] == catalog.user_id:
            if request.method == 'GET':
                return render_template('delete_catagory.html',
                                       catalog=catalog,
                                       catagory=catagory)
            elif request.method == 'POST':
                name = remove_catagory(catagory_id)
                if name:
                    flash('Catagory %s successfully removed.' % name, 'success')
                else:
                    flash('Catagory %s could not be removed.' % name, 'danger')
                return redirect(url_for('show_catagories',
                                catalog_id=catalog_id))
        else:
            flash('You must be the owner of the catalog to modify it.',
                  'danger')
            return redirect(url_for('show_catalogs'))
    else:
        flash('Catagory does not exist', 'danger')
        return redirect(url_for('show_catalogs'))

@app.route('/item/<int:item_id>/', methods=['GET'])
def show_item(item_id):
    item = db.query(Item).filter_by(id=item_id).first()
    if item:
        catagory = db.query(Catagory).filter_by(id=item.catagory_id).first()
        catalog = db.query(Catalog).filter_by(id=catagory.catalog_id).first()
        return render_template('item.html',
                               item=item,
                               catagory=catagory,
                               catalog=catalog)
    else:
        flash("No such item!", 'danger')
        return redirect(url_for('show_catalogs'))

@app.route('/item/<int:item_id>/edit/', methods=['GET','POST'])
@requires_login
def edit_item(item_id):
    item = db.query(Item).filter_by(id=item_id).first()
    if not item:
        flash("That item does not exist", 'danger')
        return redirect(url_for('show_catalogs'))
    catagory = db.query(Catagory).filter_by(id=item.catagory_id).first()
    if not catagory:
        flash("Cannot create item in catagory that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    catalog = db.query(Catalog).filter_by(id=catagory.catalog_id).first()
    if not catalog:
        flash("Cannot create item in catalog that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    if session['user_id'] != catalog.user_id:
        flash("You must be the owner of a catalog to create items",
              'danger')
        return redirect(url_for('show_catagories', catalog_id=catalog.id))
    if request.method == 'GET':
        return render_template('create_item.html',
                               catalog = catalog,
                               catagory = catagory,
                               item = item,
                               user_id = catalog.user_id)
    elif request.method == 'POST':
        item_name = request.form.get('item_name')
        if not item_name:
            flash('Item name is required.', 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   catagory = catagory,
                                   item = item,
                                   user_id = catalog.user_id)
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        row = request.form.get('row')
        rbin = request.form.get('bin')
        file = request.files['image']
        delete_image = request.form.get('delete_image')

        # If an image file was provided
        if delete_image:
            old_image = item.item_image
            if old_image:
                db.query(Image).filter_by(filename=old_image).delete()
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'],old_image))
                item.item_image = None
        elif file and allowed_image_file(file.filename):
            image = save_image(file)
            if image: # and it is valid
                # Remove old item image if it exists
                old_image = item.item_image
                if old_image:
                    db.query(Image).filter_by(filename=old_image).delete()
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'],old_image))
                item.item_image = image.filename
        item.name = item_name
        item.description = description
        item.price = price
        item.quantity = quantity
        item.row = row
        item.bin = rbin
        db.commit()
        flash("Item '%s' updated!" % item.name, 'success')
        return redirect(url_for('show_item', item_id = item.id))


@app.route('/item/<int:item_id>/delete/', methods=['GET','POST'])
@requires_login
def delete_item(item_id):
    item = db.query(Item).filter_by(id=item_id).first()
    if item:
        catagory = db.query(Catagory).filter_by(id=item.catagory_id).first()
        catalog = db.query(Catalog).filter_by(id=catagory.catalog_id).first()
        if session['user_id'] != catalog.user_id:
            flash("You must be the owner of catalog to delete items in it",
                  'danger')
            return redirect(url_for('show_catalogs'))
        if request.method == 'GET':
            return render_template('delete_item.html',
                                   item=item,
                                   catagory=catagory,
                                   catalog=catalog)
        elif request.method == 'POST':
            name = remove_item(item.id)
            if name:
                flash("Item %s deleted" % name , 'success')
            else:
                flash("Could not delete item", 'danger')
            return redirect(url_for('show_items', catagory=catagory, catalog=catalog))
    else:
        flash("Item does not exist.", 'danger')
        return redirect(url_for('show_catalogs'))

@app.context_processor
def site_utility_methods():
    def get_year():
        return datetime.datetime.now().year

    def get_catagory_rows(catalog_id):
        if catalog_id is None:
            return []
        catagories = db.query(Catagory)\
                       .filter_by(catalog_id=int(catalog_id))\
                       .all()
        row = [] 
        ret = []
        for catagory in catagories:
            row.append(catagory)
            if len(row) == 3:
                ret.append(row)
                row = []
        if len(row) != 0:
            ret.append(row)
        return ret

    def get_item_rows(catagory_id):
        items = db.query(Item).filter_by(catagory_id=int(catagory_id)).all()
        row = []
        ret = []
        for item in items:
            row.append(item)
            if len(row) == 3:
                ret.append(row)
                row = []
        if len(row) != 0:
            ret.append(row)
        return ret

    return dict(get_year=get_year,
                get_catagory_rows=get_catagory_rows,
                get_item_rows=get_item_rows,
                len=len
               )

if __name__ == '__main__':
  app.secret_key = 'Y6V6RGT8ASUYQEWYDEU9A5TXKZMXWY6H'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)

