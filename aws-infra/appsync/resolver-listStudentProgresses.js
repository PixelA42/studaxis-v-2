// AppSync JS resolver for listStudentProgresses - invokes Content Distribution Lambda
// Scan + FilterExpression on class_code (hackathon: no GSI)

import { util } from '@aws-appsync/utils';

export function request(ctx) {
    return {
        operation: 'Invoke',
        payload: {
            info: { fieldName: ctx.info.fieldName },
            arguments: ctx.arguments,
            identity: ctx.identity,
        },
    };
}

export function response(ctx) {
    if (ctx.error) {
        return util.error(ctx.error.message, ctx.error.type);
    }
    return ctx.result;
}
