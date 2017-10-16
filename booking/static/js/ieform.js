$(function(){
    // Because IE doesn't support <button form="">
    $("button[form]").click(function(e) {
        $("form#" + $(this).attr("form")).submit();
        // Make sure to prevent default behaviors, so we do not get two submits
        e.preventDefault();
        return false;
    });

    // Because IE doesn't support hiding <option>
    $.fn.extend({
        "hideOption": function() {
            this.filter(":not(span>option)").wrap("<span>").parent().hide();
            this.filter(":selected").removeAttr("selected");
        },
        "showOption": function() {
            this.filter("span>option").unwrap();
        }
    });
});