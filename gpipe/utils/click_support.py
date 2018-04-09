#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# click_support.py
#

from click import Option, UsageError


class MutuallyExclusiveOption(Option):
    """
    MutuallyExclusiveOption class is borrowed from
    https://gist.github.com/jacobtolar/fb80d5552a9a9dfc32b12a829fa21c0c
    """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        help = kwargs.get('help', '')
        if self.mutually_exclusive:
            ex_str = ', '.join(self.mutually_exclusive)
            kwargs['help'] = f'{help} NOTE: This argument is mutually exclusive with arguments: [{ex_str}]'

        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and (self.name in opts):
            raise UsageError(
                'Illegal usage: `{}` is mutually exclusive with arguments `{}`.'.format(
                    self.name,
                    ', '.join(self.mutually_exclusive)
                )
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(ctx, opts, args)
