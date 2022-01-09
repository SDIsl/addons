odoo.define('asterisk_plus.support', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var Support = AbstractAction.extend({
        template: 'asterisk_plus.support',

        init: function (parent, action) {
            this._super.apply(this, arguments);
        },

    });

    core.action_registry.add('asterisk_plus.support', Support);
});

odoo.define('asterisk_plus.change_log', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');

    var ChangeLog = AbstractAction.extend({
        template: 'asterisk_plus.change_log',

        init: function (parent, action) {
            this._super.apply(this, arguments);
        },

    });

    core.action_registry.add('asterisk_plus.change_log', ChangeLog);
});



