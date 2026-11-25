const tripProgressRoot = document.getElementById('tripProgress');

if (tripProgressRoot) {
    const tripId = tripProgressRoot.dataset.tripId;
    const storageKey = `travelai:trip:${tripId}:milestones`;
    const milestoneList = document.getElementById('milestoneList');
    const progressCount = document.getElementById('milestoneProgressCount');
    const progressBar = document.getElementById('tripProgressBar');
    let milestoneState = loadState();

    function loadState() {
        try {
            return JSON.parse(localStorage.getItem(storageKey)) || {};
        } catch {
            return {};
        }
    }

    function saveState() {
        try {
            localStorage.setItem(storageKey, JSON.stringify(milestoneState));
        } catch {
            showNotice('Milestone progress could not be saved in this browser.');
        }
    }

    function showNotice(message) {
        const notice = document.createElement('p');
        notice.className = 'milestone-empty';
        notice.textContent = message;
        milestoneList.prepend(notice);
    }

    function simpleHash(text) {
        let hash = 0;
        for (let index = 0; index < text.length; index++) {
            hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
        }
        return `milestone-${Math.abs(hash)}`;
    }

    function getMilestones() {
        const itinerary = document.querySelector('.markdown-content');
        if (!itinerary) return [];

        const headings = [...itinerary.querySelectorAll('h2, h3')]
            .map((heading) => heading.textContent.trim())
            .filter(Boolean);

        if (headings.length) return [...new Set(headings)].slice(0, 30);

        return [...itinerary.querySelectorAll('li')]
            .map((item) => item.textContent.trim())
            .filter(Boolean)
            .slice(0, 30);
    }

    function updateProgress(milestones) {
        const completed = milestones.filter((title) => milestoneState[simpleHash(title)]?.completed).length;
        const percentage = milestones.length ? Math.round((completed / milestones.length) * 100) : 0;
        progressCount.textContent = `${completed} / ${milestones.length}`;
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', String(percentage));
    }

    function makeDownloadName(fileName, milestoneTitle, photoIndex) {
        const extension = fileName.includes('.') ? fileName.split('.').pop() : 'jpg';
        const safeTitle = milestoneTitle
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '')
            .slice(0, 50) || 'trip-memory';
        return `${safeTitle}-${photoIndex + 1}.${extension}`;
    }

    function renderMilestone(title) {
        const milestoneId = simpleHash(title);
        const item = document.createElement('article');
        item.className = 'milestone-item';

        const header = document.createElement('div');
        header.className = 'milestone-header';

        const completionLabel = document.createElement('label');
        completionLabel.className = 'milestone-complete';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = Boolean(milestoneState[milestoneId]?.completed);
        checkbox.addEventListener('change', () => {
            milestoneState[milestoneId] = {
                ...milestoneState[milestoneId],
                completed: checkbox.checked,
            };
            saveState();
            item.classList.toggle('is-complete', checkbox.checked);
            updateProgress(getMilestones());
        });

        const titleElement = document.createElement('span');
        titleElement.textContent = title;
        completionLabel.append(checkbox, titleElement);

        const cameraLabel = document.createElement('label');
        cameraLabel.className = 'milestone-photo-button';
        cameraLabel.innerHTML = '<i class="fas fa-camera"></i> Take / choose photo';

        const photoInput = document.createElement('input');
        photoInput.type = 'file';
        photoInput.accept = 'image/*';
        photoInput.capture = 'environment';
        photoInput.multiple = true;
        cameraLabel.append(photoInput);

        header.append(completionLabel, cameraLabel);

        const photos = document.createElement('div');
        photos.className = 'milestone-photos';

        function addPreview(file, index) {
            if (!file.type.startsWith('image/')) {
                showNotice('Please choose an image file.');
                return;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'milestone-photo';

            const image = document.createElement('img');
            const objectUrl = URL.createObjectURL(file);
            image.src = objectUrl;
            image.alt = title;

            const saveLink = document.createElement('a');
            saveLink.className = 'milestone-photo-save';
            saveLink.href = objectUrl;
            saveLink.download = makeDownloadName(file.name, title, index);
            saveLink.innerHTML = '<i class="fas fa-download"></i> Save';
            saveLink.title = 'Save this photo to your device';

            wrapper.append(image, saveLink);
            photos.append(wrapper);
        }

        photoInput.addEventListener('change', () => {
            [...photoInput.files].forEach(addPreview);
            photoInput.value = '';
        });

        item.append(header, photos);
        item.classList.toggle('is-complete', Boolean(milestoneState[milestoneId]?.completed));
        milestoneList.append(item);
    }

    const milestones = getMilestones();
    updateProgress(milestones);

    milestones.forEach(renderMilestone);
    if (!milestones.length) {
        const empty = document.createElement('p');
        empty.className = 'milestone-empty';
        empty.textContent = 'The itinerary will appear as milestones here when day headings are available.';
        milestoneList.append(empty);
    }
}
