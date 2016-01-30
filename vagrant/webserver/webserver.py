from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from jinja2 import Template
template = Template("""
<html><body><a href="{{url}}">{{link_message}}</a>
<form method='POST' enctype='multipart/form-data' action='/'>
<h2>You said: {{message}}</h2>
<h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>
</body></html>
""")

force_url = '/theforceawakens'

class WebserverHandler(BaseHTTPRequestHandler):
    #messageForm = """<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>"""
    def do_GET(self):
        try:
            if self.path.endswith('/hello'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(template.render(url=force_url,link_message="Use the force Rae!", message=""))
            elif self.path.endswith('/theforceawakens'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(template.render(url='/hello',link_message='Back to Rae!',message=""))
        except:
            self.send_error(404, "File not found %s" % self.path)
    def do_POST(self):
        try:
            self.send_response(301)
            self.end_headers()
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                fields=cgi.parse_multipart(self.rfile, pdict)
                messagecontent = fields.get('message')
            else:
                messagecontent = ""
            self.wfile.write(template.render(url=force_url, link_message="You used the force Rae!! :D", message=messagecontent))
        except:
            pass


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
