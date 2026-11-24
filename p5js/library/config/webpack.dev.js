const { merge } = require('webpack-merge')
var webpack = require('webpack');
const common = require('./webpack.common')
const path = require('./paths')
const CopyWebpackPlugin = require('copy-webpack-plugin')

module.exports = merge(common, {
    mode: 'development',
    // Control how source maps are generated
    devtool: 'source-map',

    // Spin up a server for quick development
    devServer: {
        headers: {
            'Cache-Control': 'no-store',
        },
        historyApiFallback: true,
        open: true,
        compress: true,
        hot: true,
        port: 8080,
    },
    plugins: [
        // Enable the plugin
        new webpack.HotModuleReplacementPlugin(),

        // Copies files from target to destination folder
        new CopyWebpackPlugin({
            patterns: [
                {
                    from: path.templates,
                    globOptions: {
                        ignore: ['*.DS_Store'],
                    },
                    noErrorOnMissing: true,
                },
            ],
        }),
    ],

})