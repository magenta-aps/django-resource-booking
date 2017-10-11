$(function(){
    // Because IE doesn't support <button form="">
    $("button[form]").click(function(e) {
        var form_id = $(this).attr("form"),
            $form = $("form#" + form_id);

        // If the form is not an ancestor of the button, trigger submitting
        // of the specified form.
        if(!$(this).parents("form#" + form_id).length) {
            // Prevent double-submit if double-clicking
            if($form.attr('data-form-is-submitting')) {
                return;
            }
            $form.attr('data-form-is-submitting', "true");
            // Sumit the form
            $("form#" + form_id).submit();
            // Make sure to prevent default behaviors, so we do not get two
            // submits
            e.preventDefault();
            return false;
        }
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