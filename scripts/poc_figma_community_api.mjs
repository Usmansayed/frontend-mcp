/** POC: @figma-api/community with IDs from search API content_id */
import { Client } from '@figma-api/community';

const client = Client();

const ids = [
	'1015169662427839322', // dashboard search result
	'1035203688168086460', // documented example from gridaco
];

for (const fileId of ids) {
	console.log('\n=== community file', fileId, '===');
	try {
		const { data: document } = await client.file(fileId);
		const name = document?.name ?? document?.document?.name ?? '(unknown)';
		const pages = document?.document?.children?.length ?? 0;
		const components = Object.keys(document?.components ?? {}).length;
		const styles = Object.keys(document?.styles ?? {}).length;
		console.log('OK name:', name);
		console.log('  pages:', pages, 'components:', components, 'styles:', styles);
		console.log('  top_keys:', Object.keys(document ?? {}).slice(0, 12));
	} catch (err) {
		const status = err?.response?.status;
		const msg = err?.response?.data ?? err?.message ?? String(err);
		console.log('FAIL status:', status, 'msg:', typeof msg === 'string' ? msg.slice(0, 200) : JSON.stringify(msg).slice(0, 300));
	}
}
