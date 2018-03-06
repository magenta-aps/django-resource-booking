$(function(){
    var STATE = "state",
        STATE_NOT_LOADED = 0,
        STATE_LOADED_VISIBLE = 1,
        STATE_LOADED_HIDDEN = 2,
        STATE_BUSY = 3;
    $(".reveal-link").click(function(){
        var $this = $(this);
        var items = $this.parents(".list").find(".list-outside-limit");
        var state = $this.data(STATE) || STATE_NOT_LOADED;

        switch (state) {
            case STATE_NOT_LOADED:
                var type = $this.attr("data-item-type");
                var ids = $this.attr("data-item-ids").split(",");
                if (ids.length && ids[ids.length - 1] === "") {
                    ids.length = ids.length - 1;
                }
                $this.text($this.attr("data-text-loading"));
                items.load(
                    "/ajax/list/" + type + "/",
                    {
                        id: ids,
                        csrfmiddlewaretoken: $this.attr("data-csrf-token")
                    },
                    function (response, status, xhr) {
                        if (status === 'error') {
                            $this.text($this.attr("data-text-error"));
                            $this.data(STATE, STATE_NOT_LOADED);
                        } else {
                            items.slideDown(800, function () {
                                $this.text($this.attr("data-text-unreveal"));
                                $this.data(STATE, STATE_LOADED_VISIBLE);
                            });
                        }
                    }
                );
                state = STATE_BUSY;
                break;
            case STATE_LOADED_VISIBLE:
                items.slideUp(800, function(){
                    $this.data(STATE, STATE_LOADED_HIDDEN);
                    $this.text($this.attr("data-text-reveal"));
                });
                state = STATE_BUSY;
                break;
            case STATE_LOADED_HIDDEN:
                items.slideDown(800, function(){
                    $this.data(STATE, STATE_LOADED_VISIBLE);
                    $this.text($this.attr("data-text-unreveal"));
                });
                state = STATE_BUSY;
                break;
            case STATE_BUSY:
                break;
        }
        $this.data(STATE, state);
    });
});