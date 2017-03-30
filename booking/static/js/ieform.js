$(function(){
    // Because IE doesn't support <button form="">
    $("button[form]").click(function(){
        $("form#" + $(this).attr("form")).submit();
    });
});