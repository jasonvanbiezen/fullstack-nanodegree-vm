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

template = Template("""
<html><body><a href="{{url}}">{{link_message}}</a>
<form method='POST' enctype='multipart/form-data' action='/'>
<h2>You said: {{message}}</h2>
<h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>
</body></html>
""")

restaurantTemplate = Template("""
<html><body>
{{content}}
<hr />
{% for r in restaurants %}
    {{r.name}}<br />
    <a href='/restaurants/edit?name={{r.name}}&id={{r.id}}'>Edit</a><br />
    <a href='/restaurants/delete?name={{r.name}}&id={{r.id}}'>Delete</a><br />
    <br /><br />
{% endfor %}
</body></html>
""")

restaurantEditTemplate = Template("""
Change the name of restaurant {{id}}: <b>{{name}}</b><br />
<form method='POST' enctype='multipart/form-data' action='/restaurants/assign_new_name'>
<input name='new_name' type='text'><br />
<input type='submit' value='Confirm'>
</form>
""")

newRestaurantTemplate = Template("""
Create a new restaurant: 
<form method='POST' enctype='multipart/form-data' action='/restaurants'>
<input name='new_name' type='text'>
<input type='submit' value='Submit'>
</form>
<br />
""")

restaurantRenamedTemplate = Template("""
<html><body>
Restaurant renamed successfully!
</body></html>
""")

force_url = '/theforceawakens'

class WebserverHandler(BaseHTTPRequestHandler):
    #messageForm = """<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>"""
    def do_GET(self):
        try:
            path_parts = self.path.split('?')
            print(path_parts)
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
            elif url_path.endswith('/restaurants/edit'):
                if variables is not None and len(var_map.keys()) > 1:
                    print var_map
                    restaurant_name = var_map['name']
                    restaurant_id = var_map['id']
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    restaurants = session.query(Restaurant).all()
                    content = restaurantEditTemplate.render(name=restaurant_name, id=restaurant_id)
                    self.wfile.write(restaurantEditTemplate.render(content=content, restaurants=restaurants))
                else:
                    pass
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("<html><body><h1>Page not found!</h1></body></html>")
        except:
            self.send_error(404, "File not found %s" % self.path)
    def do_POST(self):
        try:
            if self.path.endswith('/restaurants'):
                print 'gotto correct post'
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
            elif self.path.endswith('/restaurants/assign_new_name'):
                self.send_response(301)
                self.end_headers()
                ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields=cgi.parse_multipart(self.rfile, pdict)
                    new_name = fields.get('new_name')
                else:
                    new_name = "None"
                self.wfile.write(restaurantEditTemplate.render(url=force_url, link_message="You used the force Rae!! :D", message=messagecontent))
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
