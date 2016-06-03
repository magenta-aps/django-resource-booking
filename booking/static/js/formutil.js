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
KU.TEMPLATES.htmlescape = function(html) {
    map = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&apos;'
    };

    return html.replace(/([<>&'"])/g, function(fullmatch, chr) {
        return map[chr] || fullmatch
    });
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
    var room_item_template = $('#room-item-template').html(),
        roomdata = eval($('#all_room_data').val());

    var removeElem = function() {
        $(this).parents("li").first().remove();
        if($('#chosenrooms li').length == 0) {
            $('#chosenrooms-empty').show();
        }
    };

    var addRoom = function(text, value) {
        var esc = KU.TEMPLATES.htmlescape,
            html = KU.TEMPLATES.expand(
                room_item_template,
                {
                    'value': esc(value),
                    'name': esc(text)
                }
            ),
            elem = $(html);
        elem.find("input").removeAttr("disabled");
        elem.find(".glyphicon-remove").on("click", removeElem);

        $('#chosenrooms-empty').hide();
        $('#chosenrooms').append(elem);
    };

    // Add room when selected in existing room dropdown
    $('#existingrooms').on("change", function() {
        var id = $(this).val();
        if (id) {
            addRoom(
                $(this).children("option").filter(":selected").text(),
                "id:" + id
            );
            this.selectedIndex = 0;
        }
    });

    $('#addnewroom').on("click", function() {
        var $loc = $('#id_locality'),
            val = $('#newroom').val();

        if (val) {
            if (!$loc.val()) {
                alert($(this).attr("data-no-locality-message"));
                return false;
            }
            addRoom(
                val + ", " + $loc.children("option").filter(":selected").text(),
                "new:" + val
            );
            $('#newroom').val("");
        }
    });

    $('#id_rooms_needed').on("change", function() {
        if ($(this).is(":checked")) {
            $('#rooms_needed_fields').show()
        } else {
            $('#rooms_needed_fields').hide()
        }
    }).trigger("change");

    $('#id_locality').on("change", function() {
        var val = $(this).val(),
            dropdown = $('#existingrooms')[0];

        if (dropdown == undefined) {
            return;
        }

        while (dropdown.options[1]) {
            dropdown.options[1] = null;
        }

        if (val) {
            $.each(roomdata, function() {
                if (this.locality_id == val) {
                    dropdown.options[dropdown.options.length] = new Option(
                        this.name, this.id
                    )
                }
            });
        }
    }).trigger("change");

    $('#chosenrooms .glyphicon-remove').on("click", removeElem);
    if($('#chosenrooms li').length > 0) {
        $('#chosenrooms-empty').hide();
    }

});

(function($) {
    var template_elem = $('#gymnasiefag-item-template'),
        item_template = (template_elem.get(0)||{}).innerHTML,
        $fag_select = $('#gymnasiefag-fag');

    if (!item_template || !$fag_select) {
        return
    }

    $fag_select.attr('data-reset-value', $fag_select.val())

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

        $fag_select.val($fag_select.attr('data-reset-value'));
        $('#gymnasiefag-levels input[type=checkbox]').each(function() {
            $(this).prop('checked', false)
        });
    });
    $('#gymnasiefag-list .glyphicon-remove').on('click', remove_elem);
})(jQuery);

(function($) {
    var item_template = (
            $('#grundskolefag-item-template').get(0) || {}
        ).innerHTML,
        reset_elems = [
            $('#grundskolefag-fag'),
            $('#grundskolefag-minclass'),
            $('#grundskolefag-maxclass')
        ];

    if (!item_template) {
        return
    }
    
    $.each(reset_elems, function() {
        $(this).attr('data-reset-value', $(this).val())
    });

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
            
        if (from >= 0) {
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
        
        $.each(reset_elems, function() {
            $(this).val($(this).attr('data-reset-value'))
        });
    });
    $('#grundskolefag-list .glyphicon-remove').on('click', remove_elem)
    
})(jQuery);

(function($) {
    $('select.needed-number-select').on('change', function() {
        var $this = $(this),
            val = parseInt($this.val()),
            for_id = $this.attr('data-for-id'),
            nr_container = $('#' + for_id + '-container'),
            text_container = $('#' + for_id + '-textcontainer'),
            input = nr_container.find("input").first();

        if (val > 0) {
            nr_container.show();
            text_container.hide();
            if (input.val() < 0 ) {
                if (input.attr('data-previous-value')) {
                    input.val(input.attr('data-previous-value'));
                } else {
                    input.val(1);
                }
            }
        } else {
            if (input.val() > 0) {
                input.attr('data-previous-value', input.val());
            }
            input.val(val);
            if (val == 0 || val == -2) {
                nr_container.hide();
                text_container.hide();
            } else if (val == -1) {
                nr_container.hide();
                text_container.show();
            }
        }
    }).trigger("change");
})(jQuery);

(function($){

    var isCheckbox = function(el) {
        return el.prop("nodeName")=="INPUT" && el.attr("type") == 'checkbox';
    };

    var toggle = function() {
        var $this = $(this),
            targetString = $(this).attr("data-target") || "",
            checkbox = isCheckbox($this);
        var targetList = targetString.split(/\s+/);

        var on = checkbox ? $this.prop("checked") : $this.data("toggleon");

        if (!checkbox) {
            $this.data("toggleon", on === false);
        }
        for (var i=0; i<targetList.length; i++) {
            var target = targetList[i],
                invert = false;
            if (target.indexOf("!")==0) {
                target = target.substr(1);
                invert = true;
            }
            target = $(target);
            target.toggle(!!(on ^ !invert));
        }
    };

    $("[data-toggle='hide']").each(function() {
        var $this = $(this);
        toggle.call($this);
        $this.change(toggle);
    });

}(jQuery));