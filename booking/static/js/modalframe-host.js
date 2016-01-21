window.modal = {
    nextId: 0,
    modals: {},
    close: function(id) {
        if (modal.modals[id]) {
            modal.modals[id].modal('hide');
        }
    },
    setHeight: function(id, height) {
        if (this.modals[id]) {
            this.modals[id].find("iframe").css("height", height);
        }
    },
    add: function(modal) {
        var id = modal.attr("id") || ("m" + window.modalId++);
        this.modals[id] = modal;
        return id;
    }
};


$.fn.extend({
    'hostModalIframe': function(url) {

        var id = modal.add(this);
        url += ((url.indexOf("#")==-1) ? "#":";" ) + "id=" + id;

        this.on('shown.bs.modal', function () {
            var container = $(this).find(".modal-content");
            if (!container.find("iframe").length) {
                var iframe = $("<iframe>");
                iframe.attr("src", url);
                container.append(iframe);

                iframe.load(function(){
                    var hash = iframe.get(0).contentDocument.location.hash;
                    if (!/[#;]id=[^;]/.exec(hash)) {
                        iframe.contentDocument.location.hash += (hash.indexOf("#") ? "#":";") + "id=" + id;
                        modal.modals[id].setId(id);
                    }
                });
            }
        });
    }
});