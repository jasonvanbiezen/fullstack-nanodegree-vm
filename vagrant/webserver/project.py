from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from jinja2 import Template
from urlparse import parse_qs

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


multipart_form_data = 'multipart/form-data'

restaurantTemplate = Template("""
<html>
<title>Restaurant Management</title>
<body>
<center><h1>Restaurant Management</h1></center>
{{content}}
</body>
</html>
""")

newMenuItemTemplate = Template("""
<form method='POST' enctype='%s' action='{{action_url}}'>
<table>
<tr><td>New Menu Item Name: </td><td><input name='name' type='text' value='{{default_name}}'><br /></td></tr>
<tr><td>New Menu Item Price: </td><td><input name='price' type='text' value='{{default_price}}'><br /></td></tr>
<tr><td valign='top'>New Menu Item Description: </td><td><textarea name='description type='text' rows='4' cols='80'>{{default_description}}</textarea><br /></td></tr>
</table>
<input type='submit' value='Confirm'>
</form>
<br /><br />
""" % (multipart_form_data))


@app.route('/')
@app.route('/restaurants/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    output = ''
    for i in items:
        output += i.name
        output += '</br>'
        output += i.price
        output += '</br>'
        output += i.description
        output += '</br>'
        output += '</br>'
    return output

# Task 1: Create route for newMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/new')
def newMenuItem(restaurant_id): 
    action_url = '/restaurants/%d/menu/new' % restaurant_id
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    content = "Create a new menu item for <b>%s</b>:<br /><br />" % restaurant.name
    content += newMenuItemTemplate.render(
        restaurant = restaurant,
        action_url = action_url,
        default_name = "",
        default_price = "",
        default_description = ""
    )
    content += "<h3>Existing menu items: </h3>"
    content += restaurantMenu(restaurant_id)
    return restaurantTemplate.render(content=content)

# Task 2: Create route for editMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/edit')
def editMenuItem(restaurant_id, menu_id):
    action_url = '/restaurants/%d/menu/%d/edit' % (restaurant_id, menu_id)
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menu_item = session.query(MenuItem).filter_by(id=menu_id).one()
    content = "Edit new menu <b>%s</b> item for <b>%s</b>:<br /><br />" % (menu_item.name, restaurant.name)
    content += newMenuItemTemplate.render(
        restaurant = restaurant,
        action_url = action_url,
        default_name = menu_item.name,
        default_price = menu_item.price,
        default_description = menu_item.description,
    )
    content += "<h3>Existing menu items: </h3>"
    content += restaurantMenu(restaurant_id)
    return restaurantTemplate.render(content=content)
    

# Task 3: Create a route for deleteMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/delete')
def deleteMenuItem(restaurant_id, menu_id):
    action_url = '/restaurants/%d/menu/delete' % restaurant_id
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    menu_item = session.query(MenuItem).filter_by(id=menu_id).one()
    content = """
You are about to delete menu item <b>%s</b> from restaurant <b>%s</b>.  Are you sure?
<form method='POST' enctype='%s' action='%s'>
<input type='submit' value='Delete'>
</form>
<br /><br />""" % (menu_item.name, restaurant.name, multipart_form_data, action_url)
    content += "<h3>Existing menu items: </h3>"
    content += restaurantMenu(restaurant_id)
    return restaurantTemplate.render(content=content)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)

