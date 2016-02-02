// when a field has a maxlength attribute, put a counter in the label

KU = { TEMPLATES: {} }

KU.TEMPLATES.expand = function(content, context) {
    // Replaces ##whatever## or ##WhatEver## with context['whatever']
    // globally in the template
    return content.replace(
        /##((?:\\#|[^#])+)##/g,
        function(fullmatch, key) {
            key = key.toLowerCase()
            if (key in context) {
                return context[key]
            } else {
                return fullmatch
            }
        }
    );
}

$(function(){
    var labelColonRegex = /^(.*):\s*$/;
    $("input[maxlength], textarea[maxlength]").each(function() {
        var field = $(this);
        var maxLength = parseInt(field.attr("maxlength"), 10);
        var label = $("label[for='" + this.id + "']");
        var counter = $("<span>");
        counter.attr("class","lengthcounter");
        var text = label.text();
        var colonPresent;
        if (text.match(labelColonRegex)) {
            colonPresent = true;
            label.text(text.replace(labelColonRegex, "$1"));
        }
        label.append(counter);
        if (colonPresent) {
            label.append(":")
        }

        var onUpdate = function(){
            var remaining = maxLength - field.val().length;
            counter.text("(%d tegn tilbage)".replace("%d", remaining));
        };
        field.on('keydown keypress keyup change', onUpdate);
        onUpdate();
    });
});
// Controls for adding and removing rooms
$(function() {
    // Toggle display of room edit controls according to choice in
    // room assingment dropdown
    $('#id_rooms_assignment').on("change", function() {
        if ($(this).val() == "1") {
            $('#roomsedit').hide()
        } else {
            $('#roomsedit').show()
        }
    });
    $('#id_rooms_assignment').trigger("change");

    var removeElem = function() {
        $(this).parents("li").first().remove();
    };
    
    var addRoom = function(value) {
        var elem = $('<li/>'),
            textElem = $('<span class="roomname">'),
            icon = $(
                '<span class="glyphicon glyphicon-remove" aria-hidden="true"/>'
            ),
            input = $('<input type="hidden" name="rooms"/>');

        textElem.text(value);
        input.val(value);
        icon.on("click", removeElem);
        elem.append(textElem);
        elem.append(" ");
        elem.append(icon);
        elem.append(input);
        $('#chosenrooms').append(elem);
    };

    // Add room when selected in existing room dropdown
    $('#existingrooms').on("change", function() {
        var val = $(this).val();
        if (val) {
            addRoom(val)
            this.selectedIndex = 0;
        }
    });

    $('#addnewroom').on("click", function() {
        var val = $('#newroom').val();
        if (val) {
            addRoom(val);
            $('#newroom').val("");
        }
    });
    $('#newroom').on("keydown", function(e) {
    });

    $('#id_rooms_needed').on("change", function() {
        if ($(this).is(":checked")) {
            $('#rooms_needed_fields').show()
        } else {
            $('#rooms_needed_fields').hide()
        }
    }).trigger("change");

    $('#chosenrooms .glyphicon-remove').on("click", removeElem);
});

(function($) {
    var item_template = $('#gymnasiefag-item-template').get(0).innerHTML;
    
    function check_list_display() {
        if($('#gymnasiefag-list li').length > 0) {
            $('#gymnasiefag-list').show()
            $('#gymnasiefag-empty').hide()
        } else {
            $('#gymnasiefag-list').hide()
            $('#gymnasiefag-empty').show()
        }
    }
    check_list_display();
    
    function build_description(fag_desc, level_texts) {
        var result = fag_desc
        if (level_texts.length > 0) {
            var str = '';

            // A
            str = level_texts.pop();
            // A og B
            if (level_texts.length > 0) {
                str = level_texts.pop() + " eller " + str
            }
            // X, Y, Z, A, B og C
            if (level_texts.length > 0) {
                str = level_texts.join(", ") + ", " + str
            }
            
            result = result + ' på ' + str + ' niveau';
        }
        return result
    }
    
    function remove_elem() {
        $(this).parents('li').first().remove()
        check_list_display()
    }

    $('#gymnasiefag-add').on("click", function() {
        var fag_pk = $('#gymnasiefag-fag').val(),
            level_texts = [],
            submitvalue = [fag_pk];
        if (!fag_pk) {
            alert("Du skal vælge et fag")
            return false;
        }
        $('#gymnasiefag-levels input[type=checkbox]').each(function() {
            var $this = $(this),
                val = $this.val(),
                text = $this.parent().text().trim();
            if ($this.is(":checked")) {
                level_texts.push(text);
                submitvalue.push(val)
            }
        });
        if (submitvalue.length < 2) {
            alert("Du skal vælge mindst et niveau")
            return false;
        }

        var elem_html = KU.TEMPLATES.expand(item_template, {
            'submitvalue': submitvalue.join(","),
            'description': build_description(
                $("#gymnasiefag-fag option:selected").text(),
                level_texts
            )
        });
        var elem = $(elem_html);
        elem.find('.glyphicon-remove').on('click', remove_elem);
        $('#gymnasiefag-list').append(elem);
        check_list_display();
    });
    $('#gymnasiefag-list .glyphicon-remove').on('click', remove_elem);
})(jQuery);

(function($) {
    var item_template = $('#grundskolefag-item-template').get(0).innerHTML;
    
    function check_list_display() {
        if($('#grundskolefag-list li').length > 0) {
            $('#grundskolefag-list').show()
            $('#grundskolefag-empty').hide()
        } else {
            $('#grundskolefag-list').hide()
            $('#grundskolefag-empty').show()
        }
    }
    check_list_display();
    
    function build_description(fag_desc, from, to) {
        var result = fag_desc,
            trin = [];

        from = parseInt(from) || 0;
        to = parseInt(to) || 0;
            
        if (from > 0) {
            trin.push(from)
        }

        if (to > from) {
            trin.push(to)
        }

        if (trin.length > 0) {
            result += ' på klassetrin ' + trin.join("-");
        }
        return result
    }
    
    function remove_elem() {
        $(this).parents('li').first().remove()
        check_list_display()
    }
    
    $('#grundskolefag-add').on("click", function() {
        var fag_pk = $('#grundskolefag-fag').val(),
            from = $('#grundskolefag-minclass').val() || 0,
            to = $('#grundskolefag-maxclass').val() || 0,
            submitvalue = [fag_pk, from, to];
        if (!fag_pk) {
            alert("Du skal vælge et fag")
            return false;
        }
        
        var elem_html = KU.TEMPLATES.expand(item_template, {
            'submitvalue': submitvalue.join(","),
            'description': build_description(
                $("#grundskolefag-fag option:selected").text(),
                from,
                to
            )
        });
        var elem = $(elem_html);
        elem.find('.glyphicon-remove').on('click', remove_elem);
        $('#grundskolefag-list').append(elem);
        check_list_display();
    });
    $('#grundskolefag-list .glyphicon-remove').on('click', remove_elem)
    
})(jQuery);
