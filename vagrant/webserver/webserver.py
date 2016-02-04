from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from jinja2 import Template
from urlparse import parse_qs 

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()


force_url = '/theforceawakens'
multipart_form_data = 'multipart/form-data'

template = Template("""
<html><body><a href="{{url}}">{{link_message}}</a>
<form method='POST' enctype='%s' action='/'>
<h2>You said: {{message}}</h2>
<h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>
</body></html>
""" % multipart_form_data )

restaurantTemplate = Template("""
<html><body>
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

restaurantEditTemplate = Template("""
Change the name of restaurant {{id}}: <b>{{name}}</b><br />
<form method='POST' enctype='%s' action='{{action_url}}'>
<input name='new_name' type='text'><br />
<input type='submit' value='Confirm'>
</form>
""" % multipart_form_data)

restaurantDeleteTemplate = Template("""
Are you sure you want to delete restaurant: <b>{{name}}</b><br />
<form method='POST' enctype='%s' action='{{action_url}}'>
<input type='submit' value='Delete'>
</form>
""" % multipart_form_data)

newRestaurantTemplate = Template("""
Create a new restaurant: 
<form method='POST' enctype='%s' action='/restaurants'>
<input name='new_name' type='text'>
<input type='submit' value='Submit'>
</form>
<br />
""" % multipart_form_data)

restaurantRenamedTemplate = Template("""
<html><body>
Restaurant renamed successfully!
</body></html>
""")

class WebserverHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path_parts = self.path.split('?')
            url_path = path_parts[0]
            variables = path_parts[1] if len(path_parts) > 1 else None
            var_map = parse_qs(variables) if variables is not None else dict()
            
            if url_path.endswith('/hello'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(template.render(url=force_url,link_message="Use the force Rae!", message=""))
            elif url_path.endswith(force_url):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(template.render(url='/hello',link_message='Back to Rae!',message=""))
            elif url_path.endswith('/restaurants'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                restaurants = session.query(Restaurant).all()
                self.wfile.write(restaurantTemplate.render(restaurants=restaurants, content = ""))
            elif url_path.endswith('/restaurants/new'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                content = newRestaurantTemplate.render()
                restaurants = session.query(Restaurant).all()
                self.wfile.write(restaurantTemplate.render(restaurants=restaurants, content=content)) 
            elif url_path.startswith('/restaurants') and url_path.endswith('/edit'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                url_comp = url_path.split('/')
                restaurant_id = url_comp[2]
                r = session.query(Restaurant).filter(Restaurant.id==int(restaurant_id)).first()
                restaurant_name = r.name if r is not None else ''
                restaurants = session.query(Restaurant).all()
                content = restaurantEditTemplate.render(name=restaurant_name, id=restaurant_id, action_url=url_path)
                self.wfile.write(restaurantTemplate.render(content=content, restaurants=restaurants))
            elif url_path.startswith('/restaurants') and url_path.endswith('/delete'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                url_comp = url_path.split('/')
                restaurant_id = url_comp[2]
                r = session.query(Restaurant).filter(Restaurant.id==int(restaurant_id)).first()
                restaurants = session.query(Restaurant).all()
                r_name = r.name if r is not None else ''
                content = restaurantDeleteTemplate.render(name=r_name, action_url=url_path)
                self.wfile.write(restaurantTemplate.render(content=content, restaurants=restaurants))
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("<html><body><h1>Page not found!</h1></body></html>")
        except Exception as e:
            print type(e), e.args
            self.send_error(404, "File not found %s" % self.path)
    def do_POST(self):
        try:
            path_parts = self.path.split('?')
            url_path = path_parts[0]
            variables = path_parts[1] if len(path_parts) > 1 else None
            var_map = parse_qs(variables) if variables is not None else dict()
            
            if url_path.startswith('/restaurants') and url_path.endswith('/edit'):
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == multipart_form_data:
                    fields=cgi.parse_multipart(self.rfile, pdict)
                    new_name = fields.get('new_name')
                    r_id = url_path.split('/')[2]
                    r = session.query(Restaurant).filter(Restaurant.id==r_id).first()
                    r.name = new_name[0]
                    session.commit()
                    self.send_response(301)
                    self.send_header('Location', '/restaurants')
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                else:
                    raise ValueError("Invalid restaurant name.")
            elif url_path.startswith('/restaurants') and url_path.endswith('/delete'):
                r_id = url_path.split('/')[2]
                r = session.query(Restaurant).filter(Restaurant.id==r_id).first()
                if r != None:
                    content = "Restuarant %s deleted!" % r.name
                    session.query(Restaurant).filter(Restaurant.id==r_id).delete()
                    session.commit()
                else :
                    content = "Cannot delete: No such restaurant!"
                restaurants = session.query(Restaurant).all()
                #self.send_response(301)
                #self.send_header('Location', '/restaurants')
                #self.send_header('Content-type', 'text/html')
                #self.end_headers()
                self.wfile.write(restaurantTemplate.render(restaurants=restaurants, content=content))
            elif url_path.endswith('/restaurants'):
                self.send_response(301)
                self.end_headers()
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields=cgi.parse_multipart(self.rfile, pdict)
                    new_name = fields.get('new_name')
                    if len(new_name) and len(new_name[0]) > 2:
                        new_rest = Restaurant(name=new_name[0])
                        session.add(new_rest)
                        session.commit()
                        content = "Restaurant %s added!<br /><br />" % new_name[0]
                    else:
                        content = "Bad request: name is required, and must be 3 chars or longer<br /><br />"
                else:
                    content =  "Bad request<br /><br />"
                restaurants = session.query(Restaurant).all()
                self.wfile.write(restaurantTemplate.render(restaurants=restaurants, content=content))
            else:
                self.send_response(301)
                self.end_headers()
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields=cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('message')
                else:
                    messagecontent = ""
                self.wfile.write(template.render(url=force_url, link_message="You used the force Rae!! :D", message=messagecontent))
        except Exception as e:
            print type(e), e.args
            self.send_error(404, "File not found %s" % self.path)


def main():
    try:
        port = 8080
        server = HTTPServer(('', port), WebserverHandler)
        print('Webserver started on port %s' % port)
        server.serve_forever()

    except KeyboardInterrupt:
        print('\nKeyboard Interrupt: Stopping server...')
        server.socket.close()
        print('Server stopped.')



if __name__ == '__main__':
    main()
