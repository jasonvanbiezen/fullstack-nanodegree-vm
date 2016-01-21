from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class WebserverHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path.endswith('/hello'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += """<html><body><b>hi!</b><a href="/theforceawakens">Use the force Rae!</a></body><html>"""
                self.wfile.write(output)
            elif self.path.endswith('/theforceawakens'):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += """<html><body><b>Awakens the force does!</b><br><a href="/hello">To hello page</a></body><html>"""
                self.wfile.write(output)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = """<html><body><h1>404 error</h1></body></html>"""
                self.wfile.write(output)
        except:
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
