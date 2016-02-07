from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from jinja2 import Template
from urlparse import parse_qs 

app = Flask(__name__)

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()

restaurant_url = '/restaurants'
restaurant_new_Url = '/restaurants'
restaurantTemplate = Template("""
<html>
<title>Restaurant Management</title>
<body>
<center><h1>Restaurant Management</h1></center>
<a href="/restaurants/new">Create a new restaurant</a>
<hr />
{{content}}
<hr />
{% for r in restaurants %}
    {{r.name}}<br />
    <a href='/restaurants/{{r.id}}/edit?name={{r.name}}'>Edit</a><br />
    <a href='/restaurants/{{r.id}}/delete?name={{r.name}}'>Delete</a><br />
    <br /><br />
{% endfor %}
</body></html>
""")


@app.route('/')
@app.route('/hello')
def helloWorld():
    return "Hello!"

@app.route(restaurant_url)
def restaurant():
    r = session.query(Restaurant).first()
    mis = session.query(MenuItem).filter(MenuItem.restaurant_id==r.id).all()
    content = """<html><body>"""
    content += "Restaurant: " + r.name + "<hr />"
    for mi in mis:
        content += mi.name + ": " + mi.price + "<br />"
        content += mi.description + "<br /><br />"
    content += "</body></html>"
    return content

    #restaurants = session.query(Restaurant).all()
    #return restaurantTemplate.render(restaurants=restaurants, content = "")
    

if __name__ == '__main__':
    app.debug = True # Auto-reloading & debug messaging
    app.run(host = '0.0.0.0', port = 5000)
