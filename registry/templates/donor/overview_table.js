function create_tooltip_for_donations(data) {
    var title = ``;
    Object.keys(data).forEach((slug, index) => {
        if (slug != "total")
            title += `${data[slug]["name"]}: ${data[slug]["count"]}\n`;
    });
    return `<span data-toggle="modal" data-target="#titleModal" title="${title}">❓</span>`;
}

var dataTable = null;

$(document).ready( function () {
    const columnDefs = [
        {
            "targets": "rodne_cislo",
            "render": function (data, type, row, meta) {
                if (type == "display")
                    return "<a href='"+"{{ url_for('donor.detail', rc='REPLACE_ME') }}".replace("REPLACE_ME", row.rodne_cislo) + "'>" + row.rodne_cislo + "</a>"
                else
                    return data;
            }
        }, {
            "targets": "donations",
            "render": function (data, type, row, meta) {
                return data.total + create_tooltip_for_donations(data);
            }
        }, {
            "targets": "note",
            "render": function ( data, type, row, meta ) {
              if (!data) return "";

              // Data is now structured: {emails: [], phones: [], other: "", raw: ""}
              let icons = [];

              // Add email icon(s) as mailto links
              if (data.emails && data.emails.length > 0) {
                data.emails.forEach(email => {
                  icons.push(`<a href="mailto:${email}" title="${email}">📧</a>`);
                });
              }

              // Add phone icon(s)
              if (data.phones && data.phones.length > 0) {
                const phoneList = data.phones.join("\n");
                icons.push(`<span data-toggle="modal" data-target="#titleModal" title="${phoneList}">📞</span>`);
              }

              // Add warning icon if there's other text
              if (data.other && data.other.trim()) {
                icons.push(`<span data-toggle="modal" data-target="#titleModal" title="${data.raw}">⚠️</span>`);
              }

              return icons.join(" ");
            },
            "orderable": false,
        },
    ];

    highlightOverridenValues("{{ url_for('donor.get_overrides') }}", {{ override_column_names | safe }}, columnDefs, function() {
        if (dataTable !== null)
            dataTable.draw("page");
    });

    $.fn.dataTable.ext.order.intl('cs-CZ');

    dataTable = $('#overview').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.10.21/i18n/Czech.json'
        },
        "processing": true,
        "serverSide": true,
        "stateSave": true,
        "stateDuration": -1, // -1 means session storage in the current browser window
        "ajax": "{{ url_for('donor.overview_data') }}",
        "columns": [
            {% for column_class in column_names.keys() -%}
                {"data": "{{ column_class }}"},
            {%- endfor %}
        ],
        "columnDefs": columnDefs,
        "buttons": [{
            extend: 'excel',
            text: 'Stáhnout tabulku',
            title: '',
            filename: 'export',
        }],
        "dom": "Blfrtip",
        lengthMenu: [
            [10, 25, 50, 100, -1],
            [10, 25, 50, 100, 'Všechny']
        ],
    });
} );
