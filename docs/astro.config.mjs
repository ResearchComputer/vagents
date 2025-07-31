// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeFlexoki from 'starlight-theme-flexoki'

export default defineConfig({
	integrations: [
		starlight({
			title: 'Vagents',
			customCss: [
				'./src/styles/custom.css',
			],
			plugins: [starlightThemeFlexoki()],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/vagents-ai/vagents' }],
			defaultLocale: 'en',
			locales: {
				en: {
					label: 'English',
					lang: 'en',
				},
				'zh-cn': {
					label: '简体中文',
					lang: 'zh-CN',
				},
				es: {
					label: 'Español',
					lang: 'es',
				},
			},
			sidebar: [
				{
					label: 'Guides',
					translations: {
						'zh-cn': '指南',
						'en': 'Guides',
						'es': 'Guías',
					},
					autogenerate: { directory: 'guides' },
				}
			],
		}),
	],
});
