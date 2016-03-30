$(function(){
    $(".pager").each(function(){
        var $this = $(this);
        var items = $this.find($this.attr("data-list-item"));
        var pageSize = $this.attr("data-list-size") || 10;
        if (items.length >= pageSize) {
            var page = 0;
            var lastPage = Math.ceil(items.length / pageSize) - 1;

            var showPage = function (p) {
                var beginIndex = p * pageSize;
                display = items.slice(beginIndex, beginIndex + pageSize);
                display.show();
                items.not(display).hide();
                page = p;
                updateButtons();
            };

            var firstButton = $("<button>").text("<<");
            firstButton.click(function () {
                if (page > 0) {
                    showPage(0);
                }
            });

            var prevButton = $("<button>").text("<");
            prevButton.click(function () {
                if (page > 0) {
                    showPage(page - 1);
                }
            });

            var nextButton = $("<button>").text(">");
            nextButton.click(function () {
                if (page < lastPage) {
                    showPage(page + 1);
                }
            });

            var lastButton = $("<button>").text(">>");
            lastButton.click(function () {
                if (page < lastPage) {
                    showPage(lastPage);
                }
            });

            var buttons = $().add(firstButton).add(prevButton).add(nextButton).add(lastButton);
            buttons.attr({type: "button"}).addClass("pagerbutton");

            $this.append(firstButton, prevButton, nextButton, lastButton);

            var updateButtons = function () {
                var start = $().add(firstButton).add(prevButton);
                var end = $().add(nextButton).add(lastButton);
                start.toggleClass("disabled", page == 0);
                end.toggleClass("disabled", page == lastPage);
            };

            showPage(0);
        }

    });
});