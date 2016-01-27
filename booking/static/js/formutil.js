// when a field has a maxlength attribute, put a counter in the label
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
