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