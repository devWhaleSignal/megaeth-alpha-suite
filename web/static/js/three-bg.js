/**
 * 3D Animated Background using Three.js
 */

(function() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    // Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 2000;
    const posArray = new Float32Array(particlesCount * 3);
    const colorsArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i += 3) {
        posArray[i] = (Math.random() - 0.5) * 15;
        posArray[i + 1] = (Math.random() - 0.5) * 15;
        posArray[i + 2] = (Math.random() - 0.5) * 15;
        
        // Purple to blue gradient colors
        const t = Math.random();
        colorsArray[i] = 0.4 + t * 0.2;     // R
        colorsArray[i + 1] = 0.3 + t * 0.2; // G
        colorsArray[i + 2] = 0.9 + t * 0.1; // B
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorsArray, 3));

    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.02,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });

    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    // Floating geometric shapes
    const shapes = [];
    const shapeGeometries = [
        new THREE.IcosahedronGeometry(0.3, 0),
        new THREE.OctahedronGeometry(0.25, 0),
        new THREE.TetrahedronGeometry(0.3, 0),
    ];

    const shapeMaterial = new THREE.MeshBasicMaterial({
        color: 0x8b5cf6,
        wireframe: true,
        transparent: true,
        opacity: 0.3
    });

    for (let i = 0; i < 8; i++) {
        const geometry = shapeGeometries[i % shapeGeometries.length];
        const mesh = new THREE.Mesh(geometry, shapeMaterial.clone());
        
        mesh.position.x = (Math.random() - 0.5) * 10;
        mesh.position.y = (Math.random() - 0.5) * 10;
        mesh.position.z = (Math.random() - 0.5) * 5 - 3;
        
        mesh.rotation.x = Math.random() * Math.PI;
        mesh.rotation.y = Math.random() * Math.PI;
        
        mesh.userData = {
            rotationSpeed: {
                x: (Math.random() - 0.5) * 0.01,
                y: (Math.random() - 0.5) * 0.01,
            },
            floatSpeed: Math.random() * 0.5 + 0.5,
            floatOffset: Math.random() * Math.PI * 2
        };
        
        shapes.push(mesh);
        scene.add(mesh);
    }

    // Grid
    const gridHelper = new THREE.GridHelper(20, 40, 0x1a1a2e, 0x1a1a2e);
    gridHelper.position.y = -3;
    gridHelper.material.opacity = 0.15;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    // Lines connecting particles
    const linesMaterial = new THREE.LineBasicMaterial({
        color: 0x6366f1,
        transparent: true,
        opacity: 0.1
    });

    const linesGeometry = new THREE.BufferGeometry();
    const linePositions = [];

    for (let i = 0; i < 50; i++) {
        const x1 = (Math.random() - 0.5) * 10;
        const y1 = (Math.random() - 0.5) * 10;
        const z1 = (Math.random() - 0.5) * 5 - 2;
        
        const x2 = x1 + (Math.random() - 0.5) * 3;
        const y2 = y1 + (Math.random() - 0.5) * 3;
        const z2 = z1 + (Math.random() - 0.5) * 2;
        
        linePositions.push(x1, y1, z1, x2, y2, z2);
    }

    linesGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
    const lines = new THREE.LineSegments(linesGeometry, linesMaterial);
    scene.add(lines);

    camera.position.z = 5;

    // Mouse interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    // Animation
    let time = 0;
    
    function animate() {
        requestAnimationFrame(animate);
        time += 0.01;

        // Smooth camera follow
        targetX = mouseX * 0.3;
        targetY = mouseY * 0.3;
        camera.position.x += (targetX - camera.position.x) * 0.02;
        camera.position.y += (targetY - camera.position.y) * 0.02;
        camera.lookAt(scene.position);

        // Rotate particles
        particlesMesh.rotation.y += 0.0005;
        particlesMesh.rotation.x += 0.0002;

        // Animate shapes
        shapes.forEach((shape, i) => {
            shape.rotation.x += shape.userData.rotationSpeed.x;
            shape.rotation.y += shape.userData.rotationSpeed.y;
            shape.position.y += Math.sin(time * shape.userData.floatSpeed + shape.userData.floatOffset) * 0.002;
        });

        // Rotate lines slowly
        lines.rotation.y += 0.0003;

        renderer.render(scene, camera);
    }

    animate();

    // Resize handler
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
})();
