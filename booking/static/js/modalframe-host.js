$.fn.extend({
    'hostModalIframe': function(url) {
        this.on('shown.bs.modal', function() {
            var container = $(this).find(".modal-content");
            if (!container.find("iframe").length) {
                var iframe = $("<iframe>");
                iframe.attr("src", url);
                container.append(iframe);
                iframe.load(function () {
                    var hash = iframe.get(0).contentDocument.location.hash;
                    if (hash && hash[0] == "#") {
                        /*var hashParts = hash.substr(1).split(";");
                         for (var i=0; i<hashParts.length; i++) {
                         var kvp = hashParts[i].split("=");
                         if (kvp.length == 2) {
                         var key = kvp[0],
                         value = kvp[1];
                         if (key=="height") {
                         iframe.css("height", value);
                         }
                         }
                         }*/
                        var m = /[#;]height=([\d]+)/.exec(hash);
                        if (m) {
                            iframe.css("height", m[1]);
                        }
                    }
                });
            }
        });
    }
});