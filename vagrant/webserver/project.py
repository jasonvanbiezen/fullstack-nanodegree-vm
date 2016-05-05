from flask import Flask, url_for, request, redirect, render_template, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from urlparse import parse_qs

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

multipart_form_data = 'multipart/form-data'

@app.route('/')
def homepage():
    return "Hello"

@app.route('/restaurants/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template("menu.html", restaurant = restaurant, items = items)

@app.route('/restaurants/<int:restaurant_id>/menu/json')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return jsonify(MenuItems = [i.serialize for i in items])

# Task 1: Create route for newMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/new', methods=['GET', 'POST'])
def newMenuItem(restaurant_id): 
    if request.method == 'GET':
        restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
        items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
        action_url = url_for('newMenuItem', restaurant_id = restaurant.id)
        return render_template('new_menu.html', restaurant=restaurant, action_url = action_url, default_name = "", default_price = "", default_description = "", items=items)
    elif request.method == 'POST': 
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        if name == "" or price == "":
            pass # TODO: Redirect to home
        else:
            new_item = MenuItem(name = name, price = price,
                                description = description,
                                restaurant_id = restaurant_id)
            session.add(new_item)
            session.commit()
            flash("Menu Item %s created!" % name)
            return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))

# Task 2: Create route for editMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):
    if request.method == 'GET':
        restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
        items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
        menu_item = session.query(MenuItem).filter_by(id=menu_id).one()
        action_url = url_for('editMenuItem', restaurant_id=restaurant.id, menu_id = menu_item.id)
        return render_template('new_menu.html', restaurant=restaurant, action_url = action_url, default_name = menu_item.name, default_price = menu_item.price, default_description = menu_item.description, items=items)
    elif request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        if name == "" or price == "":
            pass
        else:
            m = session.query(MenuItem).filter_by(id=menu_id).one()
            old_name = m.name
            m.name = name
            m.price = price
            m.description = description
            flash('Menu item %s updated%s!' % (old_name,
                " to %s" % m.name if m.name != old_name else ""))
            session.commit()
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))

# Task 3: Create a route for deleteMenuItem function here

@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/delete', methods=['GET','POST'])
def deleteMenuItem(restaurant_id, menu_id):
    if request.method == 'GET':
        action_url = url_for('deleteMenuItem', restaurant_id=restaurant_id, menu_id=menu_id)
        restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
        menu_item = session.query(MenuItem).filter_by(id=menu_id).one()
        return render_template("delete.html", restaurant=restaurant, menu_item=menu_item, action_url=action_url)
    elif request.method == 'POST':
        item_name = session.query(MeuuItem).filter_by(id=menu_id).one().name
        session.query(MenuItem).filter_by(id=menu_id).delete()
        session.commit()
        flash("%s deleted!" % item_name)
        return redirect(url_for('restaurantMenu', restaurant_id = restaurant_id))
    else:
        return "Page not found", 404

if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'fZi2gdqm801gl4Johjg9vMgitI3pAQuqdzdrXESte0yhxYCY5rs8g9YLy3Yg5Aaz'
    app.run(host='0.0.0.0', port=5000)

