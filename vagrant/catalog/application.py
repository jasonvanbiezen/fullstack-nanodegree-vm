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

from bfs_core_database import Base, User, Image, Catalog, Category, Item

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
    Removes catalog, and all related categories and items.

    Keyword arguments:
    catalog_id -- The row ID of the catalog to be deleted.

    Returns: name of deleted catalog, or None if delete failed.
    """
    catalog = db.query(Catalog).filter_by(id = catalog_id).first()
    if catalog:
        # First remove catalog categories, if they exist:
        categories = db.query(Category)\
                       .filter_by(catalog_id=catalog.id)\
                       .all()
        for category in categories:
            remove_category(category.id)
        name = catalog.name
        header_image = catalog.header_image
        db.query(Catalog).filter_by(id = catalog_id).delete()
        db.query(Image).filter_by(filename=header_image).delete()
        db.commit()
        if header_image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],header_image))
        return name
    return None

def remove_category(category_id):
    """ 
    Removes category, and all category items.

    Keyword arguments:
    category_id -- The row ID of the category to be deleted.
    
    Returns: name of deleted category, or None if delete failed.
    """
    category = db.query(Category).filter_by(id=category_id).first()
    if category:
        # First remove all items associated with this category
        items = db.query(Item).filter_by(category_id=category_id).all()
        for item in items:
            remove_item(item.id)
        name = category.name
        category_image = category.category_image
        db.query(Category).filter_by(id=category_id).delete()
        db.query(Image).filter_by(filename=category_image).delete()
        db.commit()
        if category_image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],category_image))
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
       return redirect(url_for('show_categories', catalog_id=new_catalog.id))

@app.route('/catalog/<int:catalog_id>/', methods=['GET'])
@app.route('/catalog/<int:catalog_id>/categories', methods=['GET'])
def show_categories(catalog_id):
    catalog = db.query(Catalog).filter_by(id = catalog_id).first()
    if not catalog:
        flash("That catalog does not exist!", 'warning')
        return redirect(url_for('show_catalogs'))
    categories = db.query(Category).filter_by(catalog_id = catalog_id).all()
    return render_template('categories.html', 
                           catalog=catalog,
                           categories=categories)

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


@app.route('/catalog/<int:catalog_id>/categories/create/',
           methods=['GET', 'POST'])
@requires_login
def create_category(catalog_id):
    catalog = db.query(Catalog).filter_by(id = catalog_id).first()
    if catalog and session['user_id'] == catalog.user_id:
        categories = db.query(Catalog)\
                       .filter_by(id=catalog_id).all()
        if request.method == 'GET':
            return render_template('create_category.html',
                                   catalog=catalog,
                                   categories=categories)
        elif request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            if name:
                catalog = db.query(Catalog)\
                            .filter_by(id = catalog_id)\
                            .first()
                existing_category = db.query(Category)\
                                      .filter(
                                        and_(Category.name==name,
                                             Category.catalog_id==catalog_id))\
                                      .first()
                if existing_category:
                    flash('Category cannot have the same name as an existing'+
                          ' category.', 'danger')
                    return redirect(url_for('create_category',
                                            catalog_id=catalog_id,
                                            name=name,
                                            description=description)
                                   )
                file = request.files['image']
                if file and allowed_image_file(file.filename):
                    image = save_image(file)
                else:
                    image = None
                new_category = Category(name=name,
                                        description=description,
                                        catalog_id=catalog_id,
                                        category_image=image.filename \
                                                       if image else None)
                db.add(new_category)
                db.commit()
                category = db.query(Category).filter_by(name=name).first()
                flash('New category ' + name + 
                      ' created in catalog ' + catalog.name, 'success')
                return redirect(url_for('show_items',
                                        category_id=category.id))
            else:
                flash('A valid name is required.', 'danger')
                return redirect(url_for('create_category',
                                        catalog_id=catalog_id,
                                        name=name,
                                        description=description))
    else:
        if catalog:
            flash('You must be the owner of a catalog to'+
                  ' create new categories.',
                  'danger')
            return redirect(url_for('show_categories',
                                    catalog_id=catalog_id))
        else:
            flash('The indicated category does not exist.', 'danger')
            return redirect(url_for('show_catalogs'))

@app.route('/category/<int:category_id>/edit/',
           methods=['GET', 'POST'])
@requires_login
def edit_category(category_id):
    category = db.query(Category).filter_by(id = category_id).first()
    if not category:
        flash("No such category.", 'danger')
        return redirect(url_for('show_catalogs'))
    catalog = db.query(Catalog).filter_by(id = category.catalog_id).first()
    if catalog and session['user_id'] == catalog.user_id:
        if request.method == 'GET':
            return render_template('create_category.html',
                                   catalog=catalog,
                                   category=category)
        elif request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            file = request.files['image']
            delete_image = request.form.get('delete_image')
            print name
            print description
            print file.filename
            print delete_image
            if name:
                if category.name != name:
                    existing_cat = db.query(Category)\
                                     .filter_by(name = name,
                                                catalog_id = catalog.id).first()
                    if existing_cat:
                        flash("Category with that name already exists in %s"%\
                                 catalog.name, "danger")
                        return render_template('create_category.html',
                                               catalog=catalog,
                                               category=category,
                                               name = name,
                                               description = description)
                if delete_image:
                    old_image = category.category_image
                    if old_image:
                        db.query(Image).filter_by(filename=old_image).delete()
                        remove_file(old_image)
                        category.category_image = None
                elif file and allowed_image_file(file.filename):
                    # If a valid image file was provided
                    image = save_image(file)
                    if image: # and it is valid
                        # Remove old item image if it exists
                        old_image = category.category_image
                        if old_image:
                            db.query(Image).filter_by(filename=old_image).delete()
                            remove_file(old_image)
                        category.category_image = image.filename
                category.name = name
                category.description = description
                db.commit()
                flash("Category '%s' updated!" % name, 'success')
                return redirect(url_for('show_items',
                                        category_id=category.id))
            else:
                flash("Category name is required.", 'danger')
    else:
        flash("You must be the owner of the category to edit it!", 'danger')
        return redirect(url_for('show_catalogs'))

@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def show_items(category_id):
    category = db.query(Category).filter_by(id=category_id).first()
    if category:
        catalog = db.query(Catalog).filter_by(id=category.catalog_id).first()
        return render_template("items.html",
                               catalog=catalog,
                               category=category)
    else:
        flash('That category does not exist.', 'danger')
        return redirect(url_for('show_categories',catalog_id=catalog_id))

@app.route('/category/<int:category_id>/item/create/', methods=['GET','POST'])
@requires_login
def create_item(category_id):
    category = db.query(Category).filter_by(id=category_id).first()
    if not category:
        flash("Cannot create item in category that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    catalog = db.query(Catalog).filter_by(id=category.catalog_id).first()
    if not catalog:
        flash("Cannot create item in catalog that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    if session['user_id'] != catalog.user_id:
        flash("You must be the owner of a catalog to create items",
              'danger')
        return redirect(url_for('show_categories', catalog_id=catalog.id))
    if request.method == 'GET':
        return render_template('create_item.html',
                               catalog = catalog,
                               category = category)
    elif request.method == 'POST':
        item_name = request.form.get('item_name')
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        row = request.form.get('row')
        rbin = request.form.get('bin')
        existing_item = db.query(Item).filter_by(name = item_name,
                                                 category_id = category.id)\
                                      .first()
        if existing_item:
            flash("An item with name '%s' already exists in the %s category"%\
                  (item_name, category.name), 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   category = category,
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
                                   category = category,
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
                                   category = category,
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
                        category_id = category.id,
                        item_image = image.filename if image else None)
        db.add(new_item)
        db.commit()
        flash('New item %s added to category %s' % \
              (item_name, category.name), 'success')
        return redirect(url_for('show_items', category_id = category.id))
        
@app.route('/category/<int:category_id>/delete/', methods=['GET','POST'])
@requires_login
def delete_category(category_id):
    category = db.query(Category).filter_by(id=category_id).first()
    if category:
        catalog_id = category.catalog_id
        catalog = db.query(Catalog).filter_by(id=catalog_id).first()
        if session['user_id'] == catalog.user_id:
            if request.method == 'GET':
                return render_template('delete_category.html',
                                       catalog=catalog,
                                       category=category)
            elif request.method == 'POST':
                name = remove_category(category_id)
                if name:
                    flash('Category %s successfully removed.' % name, 'success')
                else:
                    flash('Category %s could not be removed.' % name, 'danger')
                return redirect(url_for('show_categories',
                                catalog_id=catalog_id))
        else:
            flash('You must be the owner of the catalog to modify it.',
                  'danger')
            return redirect(url_for('show_catalogs'))
    else:
        flash('Category does not exist', 'danger')
        return redirect(url_for('show_catalogs'))

@app.route('/item/<int:item_id>/', methods=['GET'])
def show_item(item_id):
    item = db.query(Item).filter_by(id=item_id).first()
    if item:
        category = db.query(Category).filter_by(id=item.category_id).first()
        catalog = db.query(Catalog).filter_by(id=category.catalog_id).first()
        return render_template('item.html',
                               item=item,
                               category=category,
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
    category = db.query(Category).filter_by(id=item.category_id).first()
    if not category:
        flash("Cannot create item in category that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    catalog = db.query(Catalog).filter_by(id=category.catalog_id).first()
    if not catalog:
        flash("Cannot create item in catalog that doesn't exist", 'danger')
        return redirect(url_for('show_catalogs'))
    if session['user_id'] != catalog.user_id:
        flash("You must be the owner of a catalog to create items",
              'danger')
        return redirect(url_for('show_categories', catalog_id=catalog.id))
    if request.method == 'GET':
        return render_template('create_item.html',
                               catalog = catalog,
                               category = category,
                               item = item,
                               user_id = catalog.user_id)
    elif request.method == 'POST':
        item_name = request.form.get('item_name')
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        row = request.form.get('row')
        rbin = request.form.get('bin')
        file = request.files['image']
        delete_image = request.form.get('delete_image')

        if not item_name:
            flash('Item name is required.', 'danger')
            return render_template('create_item.html',
                                   catalog = catalog,
                                   category = category,
                                   item = item,
                                   user_id = catalog.user_id)

        if item.name != item_name:
            existing_item = db.query(Item)\
                              .filter_by(name=item_name,
                                         category_id=item.category_id)\
                              .first()
            if existing_item:
                flash("Item name already exists in catalog %s." % catalog.name,
                      'danger')
                return render_template('create_item.html',
                                       catalog = catalog,
                                       category = category,
                                       item = item,
                                       user_id = catalog.user_id)


        if delete_image:
            old_image = item.item_image
            if old_image:
                db.query(Image).filter_by(filename=old_image).delete()
                remove_file(old_image)
                item.item_image = None
        elif file and allowed_image_file(file.filename):
            image = save_image(file)
            if image: # and it is valid
                # Remove old item image if it exists
                old_image = item.item_image
                if old_image:
                    db.query(Image).filter_by(filename=old_image).delete()
                    remove_file(old_image)
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
        category = db.query(Category).filter_by(id=item.category_id).first()
        catalog = db.query(Catalog).filter_by(id=category.catalog_id).first()
        if session['user_id'] != catalog.user_id:
            flash("You must be the owner of catalog to delete items in it",
                  'danger')
            return redirect(url_for('show_catalogs'))
        if request.method == 'GET':
            return render_template('delete_item.html',
                                   item=item,
                                   category=category,
                                   catalog=catalog)
        elif request.method == 'POST':
            name = remove_item(item.id)
            if name:
                flash("Item %s deleted" % name , 'success')
            else:
                flash("Could not delete item", 'danger')
            return redirect(url_for('show_items', category=category, catalog=catalog))
    else:
        flash("Item does not exist.", 'danger')
        return redirect(url_for('show_catalogs'))

@app.context_processor
def site_utility_methods():
    def get_year():
        return datetime.datetime.now().year

    def get_category_rows(catalog_id):
        if catalog_id is None:
            return []
        categories = db.query(Category)\
                       .filter_by(catalog_id=int(catalog_id))\
                       .all()
        row = [] 
        ret = []
        for category in categories:
            row.append(category)
            if len(row) == 3:
                ret.append(row)
                row = []
        if len(row) != 0:
            ret.append(row)
        return ret

    def get_item_rows(category_id):
        items = db.query(Item).filter_by(category_id=int(category_id)).all()
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
                get_category_rows=get_category_rows,
                get_item_rows=get_item_rows,
                len=len
               )

if __name__ == '__main__':
  app.secret_key = 'Y6V6RGT8ASUYQEWYDEU9A5TXKZMXWY6H'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)

