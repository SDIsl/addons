odoo.define('asterisk_plus.support', function (require) {
    "use strict";

    var Widget = require('web.Widget')
    var core = require('web.core');

    var Support = Widget.extend({
        template: 'asterisk_plus.support',

        init: function (parent, action) {
            this._super.apply(this, arguments);
        },

    });

    core.action_registry.add('asterisk_plus.support', Support);
});

odoo.define('asterisk_plus.change_log', function (require) {
    "use strict";

    var Widget = require('web.Widget')
    var core = require('web.core');

    var ChangeLog = Widget.extend({
        template: 'asterisk_plus.change_log',

        init: function (parent, action) {
            this._super.apply(this, arguments);
        },

    });

    core.action_registry.add('asterisk_plus.change_log', ChangeLog);
});



