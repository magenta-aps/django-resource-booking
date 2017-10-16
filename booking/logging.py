# Thanks to https://gist.github.com/albertoalcolea/ for the code below.

import traceback


class WsgiLogErrors(object):
    """
    Dump django exceptions to apache (with mod_wsgi) error logs
    """
    def process_exception(self, request, exception):
        tb_text = traceback.format_exc()
        url = request.build_absolute_uri()
        request.META['wsgi.errors'].write(
            "Exception caught on request to %s:\n" % url +
            str(tb_text) + '\n'
        )
