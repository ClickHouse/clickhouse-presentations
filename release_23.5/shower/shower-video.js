/*!
	Video plugin for Shower, HTML presentation engine (github.com/shower/shower)

	Browser support: latest versions of all major browsers

	@url github.com/operatino/shower-video
	@author Robert Haritonov <r@rhr.me>
	@twitter @operatino
*/

/*
	TODO:
	* rerun video if it finished playback or next slide tick
	* check preload on android mobile devices
	* mark videos as played for turning off autoplay on iphone

 */

if(!(window.showerVideo && window.showerVideo.init)) {

window.showerVideo = (function(window, document, undefined) {

	var showerVideo = {},
		u = {},
		html = document.getElementsByTagName('html')[0],
		showerCssInit = 0;

	showerVideo.debug = false;

	showerVideo.isMobile = false;
	showerVideo.isIPhone = false;
	showerVideo.isIPad = false;

	/*

		Utils

	 */

	u.query = function(query) {
		return document.querySelectorAll(query);
	};

	u.forEach = function(array, callback) {
		Array.prototype.forEach.call(array, function(item){
			callback(item);
		});
	};


	/*

		Core

	 */

	showerVideo.prepareEnv = function(){
		if (navigator.userAgent.match(/Android/i)
		|| navigator.userAgent.match(/webOS/i)
		|| navigator.userAgent.match(/iPhone/i)
		|| navigator.userAgent.match(/iPad/i)
		|| navigator.userAgent.match(/iPod/i)
		|| navigator.userAgent.match(/BlackBerry/i)
		|| navigator.userAgent.match(/Windows Phone/i)
		) {
			showerVideo.isMobile = true;
			html.classList.add('mobile');
		}

		if ( navigator.userAgent.match(/iPhone/i) ) {
			showerVideo.isIPhone = true;
			html.classList.add('iphone');
		}

		if ( navigator.userAgent.match(/iPad/i) ) {
			showerVideo.isIPad = true;
			html.classList.add('ipad');
		}
	};

	showerVideo.startVideo = function(){
		//pause all videos first
		var allVideos = u.query('video');

		u.forEach(allVideos, function(el){
			el.pause();

			if (showerVideo.isMobile) { el.parentNode.style.display = 'none';}
		});

		//Fetch all videos on current slide
		var activeVideos = u.query('.slide.active video');
		u.forEach(activeVideos, function(el){
			var play = function() {
				//Resetting video
				el.currentTime = 0;
				el.play();
			};

			var prepareForPlaying = function(){
				//For triggering video load on iPad
//				el.load();
//				el.play();

				//And then pause till video fully downloaded
//				el.pause();

				//TODO: add loader

				//Waiting till video fully loads
				el.addEventListener('canplaythrough', play, false);
			};

			if(el && el.currentTime !== undefined) {
				if (el.readyState !== 4) { //HAVE_ENOUGH_DATA

					if (showerVideo.debug) console.log('Video not ready');

					if(showerVideo.isMobile && showerCssInit === 0) {
						//TODO: add loader
						//TODO: on first page visit with video, add play button

						//initing video after first Shower CSS init, to avoid CPU load bottleneck
						setTimeout(function(){
							//TODO: move this init to Full mode check
							showerCssInit = 1;

							el.parentNode.style.display = 'block';

							prepareForPlaying();
						}, 700);

					} else {

						//Init video for mobile devices
						if (showerVideo.isMobile) { el.parentNode.style.display = 'block';}

						prepareForPlaying();
					}

				} else {
					if (showerVideo.debug) console.log('Video is ready');

					if (showerVideo.isMobile) { el.parentNode.style.display = 'block';}

					play();
				}
			}
		});
	};

	showerVideo.startGif = function(){
		var activeSlideGifs = u.query('.slide.active .gif'),
			allGifs = u.query('.slide .gif');

		if( activeSlideGifs.length !== 0) {

			u.forEach(activeSlideGifs, function(item){
				if (item.classList.contains('real')) {
					item.style.display = 'block';
				} else {
					item.style.display  = 'none';
				}
			});

		} else {

			u.forEach(allGifs, function(item){
				if (item.classList.contains('real')) {
					item.style.display  = 'none';
				} else {
					item.style.display  = 'block';
				}
			});
		}
	};

	showerVideo.init = function(){
		showerVideo.prepareEnv();

		// Listen for the Slide Switch event
		// TODO: wait for proper API implementation in Shower
		document.addEventListener('keyup', function (e) {
			showerVideo.startVideo();
			showerVideo.startGif();
		}, false);
	};


	/*

		Init

	 */

	showerVideo.init();

	return showerVideo;

})(this, this.document);

}