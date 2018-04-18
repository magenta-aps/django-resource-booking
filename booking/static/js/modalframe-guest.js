window.modal = {
    parent: window.parent && window.parent.modal,
    setId: function(id) {
        this.id = id;
        $("form").append("<input type='hidden' name='modalid' value='"+id+"'/>");
        $("form").attr("action", ($("form").attr("action") || '') + "#id=" + id);
    },
    close: function() {
        this.parent.close(this.id);
    },
    setHeight: function(height) {
        if (this.parent) {
            this.parent.setHeight(this.id, height);
        }
    },
    obtainChildrenHeight: function(element) {
        var height = 0;
        $(element).children().not("script").each(function() {
            if (this.nodeName === "FORM") {
                height += window.modal.obtainChildrenHeight(this);
            } else {
                height += $(this).outerHeight(true);
            }
        });
        return height;
    },
    documentHeight: 0,
    updateHeight: function() {
        var height = window.modal.obtainChildrenHeight(document.body);
        if (height != this.documentHeight) {
            this.documentHeight = height;
            this.setHeight(height);
        }
    },
    on: function (event, fct) {
        this.parent.on(this.id, event, fct);
    }
};
(function(){
    var m = /[#;]id=([^;]+)/.exec(document.location.hash);
    if (m) {
        modal.setId(m[1]);
    }
})();


$(function(){
    if (window.modal.parent) {
        setTimeout(modal.updateHeight.bind(modal), 0);
        $("*[data-dismiss='modal']").click(modal.close.bind(modal));
    }
});

$(function(){
    if (window.modal.parent) {

        // Show a formpart, with the relevant navigation buttons
        var show = function (formpart) {
            if (typeof(formpart) === "string") {
                formpart = $(formpart);
            }
            if (formpart.length) {
                // Show 'previous' button as defined by the "data-prevbutton" attribute
                var prevButtonId = formpart.attr("data-prevbutton");
                var prevButton = prevButtonId && $("#" + prevButtonId) || null;
                if (prevButton) {
                    prevButton.show();
                }

                // Show 'next' button as defined by the "data-nextbutton" attribute
                var nextButtonId = formpart.attr("data-nextbutton");
                var nextButton = nextButtonId && $("#" + nextButtonId) || null;
                if (nextButton) {
                    nextButton.show();
                }

                // Hide other navigation buttons
                $(".formpartbutton").not(prevButton).not(nextButton).hide();

                // Show formpart
                formpart.show();

                // Hide other formparts
                $(".formpart").not(formpart).hide();

                modal.updateHeight();
            }
        };

        // Handle clicks on the 'previous' button
        $("*[data-formpart-action='prev']").click(function () {
            var prevId = $(".formpart:visible").attr("data-prev");
            if (prevId) {
                show("#" + prevId);
            }
        });
        // Handle clicks on the 'next' button
        $("*[data-formpart-action='next']").click(function () {
            var nextId = $(".formpart:visible").attr("data-next");
            if (nextId) {
                show("#" + nextId);
            }
        });

        // Show the formpart that has data-first set
        var firstFormPart = $(".formpart[data-first]");
        if (firstFormPart.length) {
            show(firstFormPart);
        }

        // setInterval(modal.updateHeight.bind(modal), 500);
        $(document).resize(modal.updateHeight.bind(modal));
        $("input,select").change(modal.updateHeight.bind(modal));
    }
});