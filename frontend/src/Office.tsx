import { Suspense, useRef, useState, useMemo, useEffect } from "react";
import { Canvas, useFrame, ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Grid, ContactShadows, Float } from "@react-three/drei";
import * as THREE from "three";
export const departments = [
  "AI Manager",
  "Video Editor",
  "Worldwide Lead Finder",
  "Gmail Email Agent",
  "Sales Agent",
  "Marketing Agent",
  "Customer Support",
  "Finance Agent",
  "Analytics Agent",
  "Operations Agent",
];
function OfficeLabel({
  name,
  active,
  position,
}: {
  name: string;
  active: boolean;
  position: [number, number, number];
}) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 96;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#101d30ee";
    ctx.fillRect(0, 0, 640, 96);
    ctx.strokeStyle = active ? "#55d9b4" : "#3a526f";
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, 636, 92);
    ctx.fillStyle = active ? "#55f3c1" : "#bdd2e9";
    ctx.font = "500 34px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(name, 320, 48);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, [name, active]);
  useEffect(() => () => texture.dispose(), [texture]);
  return (
    <sprite position={position} scale={[1.85, 0.278, 1]} renderOrder={10}>
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}
function Employee({
  position,
  index,
  active,
  onSelect,
}: {
  position: [number, number, number];
  index: number;
  active: boolean;
  onSelect: (name: string) => void;
}) {
  const ref = useRef<THREE.Group>(null);
  const [hover, setHover] = useState(false);
  useFrame(({ clock }) => {
    if (ref.current)
      ref.current.position.y =
        0.92 + Math.sin(clock.elapsedTime * 2 + index) * 0.045;
  });
  const color = active ? "#55f3c1" : index % 2 ? "#9477ff" : "#48c9fa";
  return (
    <group
      position={position}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        onSelect(departments[index]);
      }}
      onPointerOver={() => {
        setHover(true);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        setHover(false);
        document.body.style.cursor = "auto";
      }}
    >
      <mesh position={[0, 0.46, 0]} castShadow>
        <boxGeometry args={[1.55, 0.12, 0.95]} />
        <meshStandardMaterial
          color={hover ? "#30465f" : "#1a2b45"}
          metalness={0.5}
          roughness={0.35}
        />
      </mesh>
      {[-0.62, 0.62].map((x) => (
        <mesh key={x} position={[x, 0.2, 0]}>
          <boxGeometry args={[0.09, 0.4, 0.7]} />
          <meshStandardMaterial color="#22344d" />
        </mesh>
      ))}
      <mesh position={[0, 0.88, -0.25]}>
        <boxGeometry args={[0.88, 0.55, 0.065]} />
        <meshStandardMaterial color="#0c1728" />
      </mesh>
      <mesh position={[0, 0.88, -0.208]}>
        <planeGeometry args={[0.78, 0.44]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hover ? 1 : 0.35}
        />
      </mesh>
      <mesh position={[0, 0.62, -0.25]}>
        <cylinderGeometry args={[0.045, 0.08, 0.22]} />
        <meshStandardMaterial color="#516d85" />
      </mesh>
      <mesh position={[0, 0.55, 0.15]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[0.52, 0.18]} />
        <meshStandardMaterial color="#344c69" />
      </mesh>
      <group ref={ref} position={[0, 0.92, 0.65]}>
        <mesh castShadow>
          <capsuleGeometry args={[0.15, 0.25, 4, 8]} />
          <meshStandardMaterial
            color={index % 2 ? "#7c68df" : "#238fae"}
            metalness={0.4}
            roughness={0.35}
          />
        </mesh>
        <mesh position={[0, 0.31, 0]}>
          <sphereGeometry args={[0.18, 16, 16]} />
          <meshStandardMaterial color="#cedceb" />
        </mesh>
        <mesh position={[0, 0.32, -0.145]}>
          <boxGeometry args={[0.23, 0.075, 0.07]} />
          <meshStandardMaterial
            color="#101b31"
            emissive={color}
            emissiveIntensity={0.4}
          />
        </mesh>
      </group>
      <mesh position={[0, 0.015, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.87, 0.9, 48]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={hover ? 0.8 : 0.15}
        />
      </mesh>
      <OfficeLabel
        name={departments[index]}
        active={active}
        position={[0, 1.65, 0]}
      />
    </group>
  );
}
export default function Office({
  active,
  onSelect,
}: {
  active: string[];
  onSelect: (name: string) => void;
}) {
  return (
    <Canvas
      shadows
      camera={{ position: [10, 11, 12], fov: 40 }}
      dpr={[1, 1.75]}
    >
      <color attach="background" args={["#0b1223"]} />
      <fog attach="fog" args={["#0b1223", 20, 42]} />
      <ambientLight intensity={0.8} />
      <directionalLight
        position={[3, 12, 5]}
        intensity={2}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <pointLight position={[-4, 3, -3]} color="#865cff" intensity={25} />
      <pointLight position={[5, 3, 2]} color="#29bfff" intensity={20} />
      <Suspense fallback={null}>
        <mesh receiveShadow position={[0, -0.16, 0]}>
          <boxGeometry args={[14, 0.3, 10]} />
          <meshStandardMaterial
            color="#111e33"
            metalness={0.3}
            roughness={0.6}
          />
        </mesh>
        <Grid
          position={[0, 0.005, 0]}
          args={[14, 10]}
          cellSize={0.5}
          cellThickness={0.3}
          cellColor="#263a55"
          sectionSize={2}
          sectionColor="#304c70"
          fadeDistance={30}
        />
        <mesh position={[-6.7, 0.65, 0]}>
          <boxGeometry args={[0.15, 1.3, 10]} />
          <meshStandardMaterial color="#1d3150" transparent opacity={0.7} />
        </mesh>
        <mesh position={[0, 0.65, -4.7]}>
          <boxGeometry args={[14, 1.3, 0.15]} />
          <meshStandardMaterial color="#233857" transparent opacity={0.7} />
        </mesh>
        {departments.map((_, i) => (
          <Employee
            key={i}
            index={i}
            position={[((i % 5) - 2) * 2.5, 0, (Math.floor(i / 5) - 0.5) * 3.8]}
            active={active.includes(departments[i])}
            onSelect={onSelect}
          />
        ))}
        <Float speed={1.4} floatIntensity={0.25}>
          <mesh position={[0, 2.8, 0]} rotation={[0, Math.PI / 4, 0]}>
            <octahedronGeometry args={[0.4]} />
            <meshStandardMaterial
              color="#6be9f4"
              emissive="#24a7bb"
              emissiveIntensity={0.7}
              wireframe
            />
          </mesh>
        </Float>
        <ContactShadows
          position={[0, -0.01, 0]}
          opacity={0.3}
          scale={20}
          blur={2}
          far={5}
        />
        <OrbitControls
          makeDefault
          minDistance={8}
          maxDistance={24}
          minPolarAngle={0.25}
          maxPolarAngle={Math.PI / 2.2}
          target={[0, 0.2, 0]}
        />
      </Suspense>
    </Canvas>
  );
}
