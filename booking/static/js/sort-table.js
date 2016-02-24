$(function() {
    $("table.sortable").each(function() {
        var $this = $(this);
        var columns = [];

        $this.find("th.sort").each(function(){
            columns.push($(this).index());
        });

        $this.tableSort({
            indexes: columns
        });
    });
});