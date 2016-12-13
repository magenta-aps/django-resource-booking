//Search-list.html start:
$('.collapse').on('show.bs.collapse', function() {
    $(this).parent().find(".caret").removeClass("caret").addClass("caret-up");
}).on('hide.bs.collapse', function() {
    $(this).parent().find(".caret-up").removeClass("caret-up").addClass("caret");
});
$('#filters').on('show.bs.collapse', function() {
    $(this).prev().find(".glyphicon").toggleClass("glyphicon-chevron-down glyphicon-chevron-up");
});
$('#filters').on('hide.bs.collapse', function() {
    $(this).prev().find(".glyphicon").toggleClass("glyphicon-chevron-up glyphicon-chevron-down");
});

//Search-list.html end
$("#reset-btn").click(function() {
    $("#searchBox").val("");
    $("form").trigger("submit")
});

// Automatically submit the search form whenever the filters are changed
$(function() {
    $('#filter-search-results input[type=checkbox]').on('change', function() {
        $(this.form).trigger("submit")
    });
    $('#filter-search-results input.datepicker').on('changeDate', function() {
        $(this.form).trigger("submit")
    });
});

// Move child items to a destination (handy when django just doesn't let you put elements where they should be
// Usage: put items in a container and add attributes: <div data-move="input" data-target="#move_{data-attr}" data-attr="value"><input type="checkbox" value="hey"></div>
// Also add or modify a recipient container: <div id="move_hey"></div>
// Items will be selected according to the data-move attribute, and moved to the container specified by data-target, replacing {data-attr} with the item attribute specified in data-attr
$("[data-move][data-target]").each(function(){
    var $this = $(this),
        subject = $this.find($this.attr("data-move")),
        attr = $this.attr("data-attr"),
        target = $this.attr("data-target");
    subject.each(function(){
        var item = $(this),
            destination = $(target.replace("{data-attr}", item.attr(attr)));
        if (item.length && destination.length) {
            destination.append(item);
        }
    });
    $this.remove();
});

$.fn.enable = function(doEnable, key) {
    doEnable = !!doEnable;
    this.each(function(){
        var $this = $(this);
        var locks = $this.data("disable") || {};
        locks[key] = doEnable;
        var locked = false;
        for (var k in locks) {
            if (locks.hasOwnProperty(k)) {
                if (locks[k] === false) {
                    locked = true;
                }
            }
        }
        if (locked) {
            $this.attr("disabled", "disabled");
        } else {
            $this.removeAttr("disabled");
        }
        $this.data("disable", locks);
    });
};
