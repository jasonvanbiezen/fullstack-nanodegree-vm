from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi

class WebserverHandler(BaseHTTPRequestHandler):
    #messageForm = """<form method='POST' enctype='multipart/form-data' action='/hello'><h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>"""
    def do_GET(self):
        try:
            if self.path.endswith('/hello'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += """<html><body><b>hi!</b><a href="/theforceawakens">Use the force Rae!</a>"""
                output += """<form method='POST' enctype='multipart/form-data' action='/'><h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>"""
                output += """</body><html>"""
                self.wfile.write(output)
            elif self.path.endswith('/theforceawakens'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += """<html><body><b>Awakens the force does!</b><br><a href="/hello">To hello page</a>"""
                output += """<form method='POST' enctype='multipart/form-data' action='/'><h2>What would you like me to say?<h2><input name='message' type='text'><input type='submit' value='Submit'></form>"""
                output += """</body><html>"""
                self.wfile.write(output)
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
                output = ""
                output +=  "<html><body>"
                output += " <h2> Okay, how about this: </h2>"
                output += "<h1> %s </h1>" % messagecontent[0]
                output += """<form method='POST' enctype='multipart/form-data' action='/'><h2>What would you like me to say?</h2><input name="message" type="text" ><input type="submit" value="Submit"></form>"""
                output += "</html></body>"
            else:
                output="<html><body><h1>no message</h1></body></html>"
            self.wfile.write(output)
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
