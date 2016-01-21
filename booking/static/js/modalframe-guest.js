window.modal = {
    parent: window.parent.modal,
    setId: function(id) {
        this.id = id;
    },
    close: function() {
        this.parent.close(this.id);
    },
    setHeight: function(height) {
        this.parent.setHeight(this.id, height);
    }
};
(function(){
    var m = /[#;]id=([^;]+)/.exec(document.location.hash);
    if (m) {
        modal.id = m[1];
    }
})();


$(function(){
    modal.setHeight($(document).height());
    $("*[data-dismiss='modal']").click(modal.close.bind(modal));
});