// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeFlexoki from 'starlight-theme-flexoki'

export default defineConfig({
	integrations: [
		starlight({
			title: 'vAgents',
			plugins: [starlightThemeFlexoki()],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/eth-easl/vagents' }],
			sidebar: [
				{
					label: 'Guides',
					items: [
						{ label: 'Example: Deep Research', slug: 'guides/example-deep-research' },
					],
				},
				{
					label: 'Reference',
					autogenerate: { directory: 'reference' },
				},
			],
		}),
	],
});
