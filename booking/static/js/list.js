$(function(){
    $(".reveal-link").click(function(){
        var $this = $(this);
        var items = $this.parents(".list").find(".list-outside-limit");
        if (items.is(":visible")) {
            items.slideUp(800);
            $this.text($this.attr("data-text-reveal"));
        } else {
            items.slideDown(800);
            $this.text($this.attr("data-text-unreveal"));
        }

    });
});